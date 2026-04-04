import datetime
from collections import defaultdict
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.account import UserAccount
from src.models.mcc_category import MccCategory
from src.models.transaction import UserTransaction
from src.schemas.balance import (
    AccountBalanceResponse,
    BurnRateResponse,
    CategorySpendingResponse,
    DailyExpensesItem,
    DailySummaryResponse,
    IncomeVsExpensesResponse,
    UserBalanceSummary,
)


class BalanceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_current_balance(self, account_id: str) -> AccountBalanceResponse | None:
        account = await self.session.execute(
            select(UserAccount).where(UserAccount.account_id == account_id)
        )
        account = account.scalar_one_or_none()

        if not account:
            return None

        result = await self.session.execute(
            select(UserTransaction.balance, UserTransaction.time)
            .where(UserTransaction.account_id == account_id)
            .order_by(UserTransaction.time.desc())
            .limit(1)
        )
        row = result.first()

        return AccountBalanceResponse(
            account_id=account_id,
            currency_code=account.currency_code or 0,
            balance=row.balance if row else 0,
            display_name=account.display_name,
            last_transaction_time=row.time if row else None,
        )

    async def get_user_balances(self, user_id: UUID) -> list[AccountBalanceResponse]:
        accounts = await self.session.execute(
            select(UserAccount).where(UserAccount.user_id == user_id)
        )
        accounts = accounts.scalars().all()
        print(f'Found {accounts} accounts')
        results = []
        for account in accounts:
            last_tx = await self.session.execute(
                select(UserTransaction.balance, UserTransaction.time)
                .where(UserTransaction.account_id == account.account_id)
                .order_by(UserTransaction.time.desc())
                .limit(1)
            )
            row = last_tx.first()
            print(f'Found {row} transactions')
            results.append(AccountBalanceResponse(
                account_id=account.account_id,
                currency_code=account.currency_code or 0,
                balance=row.balance if row else 0,
                display_name=account.display_name,
                last_transaction_time=row.time if row else None,
            ))

        return results

    async def get_user_balance_summary(self, user_id: UUID) -> UserBalanceSummary:
        balances = await self.get_user_balances(user_id)

        totals: dict[int, int] = defaultdict(int)
        for b in balances:
            totals[b.currency_code] += b.balance

        return UserBalanceSummary(
            accounts=balances,
            totals_by_currency=dict(totals),
        )

    async def get_balance_history(
        self,
        user_id: UUID,
        from_timestamp: int,
        to_timestamp: int,
        account_id: str | None = None,
    ) -> list[DailySummaryResponse]:
        tx_date = func.date(func.to_timestamp(UserTransaction.time))

        # Subquery to find max time per day for closing balance
        max_time_subq = (
            select(
                tx_date.label("date"),
                func.max(UserTransaction.time).label("max_time"),
            )
            .where(
                UserTransaction.user_id == user_id,
                UserTransaction.time >= from_timestamp,
                UserTransaction.time < to_timestamp,
            )
        )
        if account_id:
            max_time_subq = max_time_subq.where(UserTransaction.account_id == account_id)
        max_time_subq = max_time_subq.group_by(tx_date).subquery()

        # Closing balance: balance of the last transaction each day
        closing_balance_subq = (
            select(
                UserTransaction.time,
                UserTransaction.balance.label("closing_balance"),
            )
            .where(
                UserTransaction.user_id == user_id,
                UserTransaction.time >= from_timestamp,
                UserTransaction.time < to_timestamp,
            )
        )
        if account_id:
            closing_balance_subq = closing_balance_subq.where(
                UserTransaction.account_id == account_id
            )
        closing_balance_subq = closing_balance_subq.subquery()

        income_expr = func.coalesce(
            func.sum(case((UserTransaction.amount > 0, UserTransaction.amount))), 0
        )
        expenses_expr = func.coalesce(
            func.sum(case((UserTransaction.amount < 0, func.abs(UserTransaction.amount)))), 0
        )

        query = (
            select(
                tx_date.label("date"),
                income_expr.label("income"),
                expenses_expr.label("expenses"),
                func.count().label("transaction_count"),
            )
            .where(
                UserTransaction.user_id == user_id,
                UserTransaction.time >= from_timestamp,
                UserTransaction.time < to_timestamp,
            )
        )
        if account_id:
            query = query.where(UserTransaction.account_id == account_id)

        query = query.group_by(tx_date).order_by(tx_date)
        result = await self.session.execute(query)
        daily_rows = result.all()

        # Get closing balances
        closing_query = (
            select(
                max_time_subq.c.date,
                closing_balance_subq.c.closing_balance,
            )
            .join(
                closing_balance_subq,
                closing_balance_subq.c.time == max_time_subq.c.max_time,
            )
        )
        closing_result = await self.session.execute(closing_query)
        closing_map = {row.date: row.closing_balance for row in closing_result.all()}

        return [
            DailySummaryResponse(
                date=row.date,
                income=row.income,
                expenses=row.expenses,
                net=row.income - row.expenses,
                closing_balance=closing_map.get(row.date, 0),
                transaction_count=row.transaction_count,
            )
            for row in daily_rows
        ]

    async def get_income_vs_expenses(
        self,
        user_id: UUID,
        from_timestamp: int,
        to_timestamp: int,
        account_id: str | None = None,
    ) -> IncomeVsExpensesResponse:
        income_expr = func.coalesce(
            func.sum(case((UserTransaction.amount > 0, UserTransaction.amount))), 0
        )
        expenses_expr = func.coalesce(
            func.sum(case((UserTransaction.amount < 0, func.abs(UserTransaction.amount)))), 0
        )

        query = select(income_expr.label("income"), expenses_expr.label("expenses")).where(
            UserTransaction.user_id == user_id,
            UserTransaction.time >= from_timestamp,
            UserTransaction.time < to_timestamp,
        )
        if account_id:
            query = query.where(UserTransaction.account_id == account_id)

        result = await self.session.execute(query)
        row = result.one()

        total_income = row.income
        total_expenses = row.expenses
        net_savings = total_income - total_expenses
        savings_rate = (net_savings / total_income * 100) if total_income > 0 else None

        return IncomeVsExpensesResponse(
            period_start=datetime.date.fromtimestamp(from_timestamp),
            period_end=datetime.date.fromtimestamp(to_timestamp),
            total_income=total_income,
            total_expenses=total_expenses,
            net_savings=net_savings,
            savings_rate=round(savings_rate, 2) if savings_rate is not None else None,
        )

    async def get_burn_rate(
        self,
        user_id: UUID,
        from_timestamp: int,
        to_timestamp: int,
        account_id: str | None = None,
    ) -> BurnRateResponse:
        # Розширюємо період на 30 днів назад для ковзної середньої
        extended_from = from_timestamp - 30 * 86400

        tx_date = func.date(func.to_timestamp(UserTransaction.time))
        expenses_expr = func.coalesce(
            func.sum(case((UserTransaction.amount < 0, func.abs(UserTransaction.amount)))), 0
        )

        query = (
            select(tx_date.label("date"), expenses_expr.label("expenses"))
            .where(
                UserTransaction.user_id == user_id,
                UserTransaction.time >= extended_from,
                UserTransaction.time < to_timestamp,
            )
            .group_by(tx_date)
            .order_by(tx_date)
        )
        if account_id:
            query = query.where(UserTransaction.account_id == account_id)

        result = await self.session.execute(query)
        rows = result.all()

        # Словник дата → витрати
        expenses_map: dict[datetime.date, int] = {row.date: row.expenses for row in rows}

        # Повний діапазон дат від extended_from до to_timestamp (UTC)
        _utc = datetime.timezone.utc
        extended_start = datetime.datetime.fromtimestamp(extended_from, tz=_utc).date()
        period_start = datetime.datetime.fromtimestamp(from_timestamp, tz=_utc).date()
        period_end = datetime.datetime.fromtimestamp(to_timestamp, tz=_utc).date() - datetime.timedelta(days=1)

        all_dates: list[datetime.date] = []
        current = extended_start
        while current <= period_end:
            all_dates.append(current)
            current += datetime.timedelta(days=1)

        # Ковзні середні для кожного дня
        def moving_avg(target_date: datetime.date, window: int) -> int | None:
            total = 0
            for i in range(window):
                d = target_date - datetime.timedelta(days=i)
                total += expenses_map.get(d, 0)
            return total // window

        # Формуємо daily_breakdown тільки для запитаного періоду
        daily_breakdown: list[DailyExpensesItem] = []
        total_expenses = 0
        days_in_period = 0

        current = period_start
        while current <= period_end:
            exp = expenses_map.get(current, 0)
            total_expenses += exp
            days_in_period += 1
            daily_breakdown.append(DailyExpensesItem(
                date=current,
                expenses=exp,
                moving_avg_7d=moving_avg(current, 7),
            ))
            current += datetime.timedelta(days=1)

        avg_daily = total_expenses // days_in_period if days_in_period > 0 else 0
        last_day = period_end if days_in_period > 0 else None

        ma_7d = moving_avg(last_day, 7) if last_day else None
        ma_30d = moving_avg(last_day, 30) if last_day else None

        # Попередній період для тренду
        prev_from = from_timestamp - days_in_period * 86400
        prev_to = from_timestamp

        prev_query = (
            select(expenses_expr.label("expenses"))
            .where(
                UserTransaction.user_id == user_id,
                UserTransaction.time >= prev_from,
                UserTransaction.time < prev_to,
            )
        )
        if account_id:
            prev_query = prev_query.where(UserTransaction.account_id == account_id)

        prev_result = await self.session.execute(prev_query)
        prev_total = prev_result.scalar_one()

        prev_avg = prev_total // days_in_period if days_in_period > 0 else 0
        trend = (
            round((avg_daily - prev_avg) / prev_avg * 100, 1)
            if prev_avg > 0
            else None
        )

        return BurnRateResponse(
            period_start=period_start,
            period_end=period_end,
            total_expenses=total_expenses,
            days_in_period=days_in_period,
            avg_daily_expenses=avg_daily,
            moving_avg_7d=ma_7d,
            moving_avg_30d=ma_30d,
            prev_period_avg_daily=prev_avg if prev_avg > 0 else None,
            trend_percentage=trend,
            daily_breakdown=daily_breakdown,
        )

    async def get_spending_by_category(
        self,
        user_id: UUID,
        from_timestamp: int,
        to_timestamp: int,
        account_id: str | None = None,
    ) -> list[CategorySpendingResponse]:
        amount_sum = func.sum(func.abs(UserTransaction.amount))
        tx_count = func.count()

        query = (
            select(
                MccCategory.category_name,
                MccCategory.display_name_uk,
                amount_sum.label("total_amount"),
                tx_count.label("transaction_count"),
            )
            .join(MccCategory, MccCategory.mcc_code == UserTransaction.mcc)
            .where(
                UserTransaction.user_id == user_id,
                UserTransaction.amount < 0,
                UserTransaction.time >= from_timestamp,
                UserTransaction.time < to_timestamp,
            )
            .group_by(MccCategory.category_name, MccCategory.display_name_uk)
            .order_by(amount_sum.desc())
        )
        if account_id:
            query = query.where(UserTransaction.account_id == account_id)

        result = await self.session.execute(query)
        rows = result.all()

        total = sum(row.total_amount for row in rows) or 1

        return [
            CategorySpendingResponse(
                category_name=row.category_name,
                display_name=row.display_name_uk,
                total_amount=row.total_amount,
                transaction_count=row.transaction_count,
                percentage=round(row.total_amount / total * 100, 2),
            )
            for row in rows
        ]
