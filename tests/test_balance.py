import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.account import UserAccount
from src.models.transaction import UserTransaction
from src.models.user import User
from src.services.balance import BalanceService


pytestmark = pytest.mark.asyncio


class TestGetCurrentBalance:

    async def test_returns_balance_from_latest_transaction(
        self, session: AsyncSession, test_account: UserAccount, sample_transactions,
    ):
        service = BalanceService(session)
        result = await service.get_current_balance(test_account.account_id)

        assert result is not None
        assert result.account_id == test_account.account_id
        assert result.balance == 4559500  # last transaction balance
        assert result.currency_code == 980
        assert result.display_name == "5375 **** 1234"

    async def test_returns_none_for_unknown_account(self, session: AsyncSession):
        service = BalanceService(session)
        result = await service.get_current_balance("nonexistent_account")
        assert result is None

    async def test_returns_zero_balance_when_no_transactions(
        self, session: AsyncSession, test_account: UserAccount,
    ):
        service = BalanceService(session)
        result = await service.get_current_balance(test_account.account_id)

        assert result is not None
        assert result.balance == 0
        assert result.last_transaction_time is None


class TestGetUserBalances:

    async def test_returns_all_accounts(
        self, session: AsyncSession, test_user: User, test_account, sample_transactions,
    ):
        service = BalanceService(session)
        balances = await service.get_user_balances(test_user.id)

        assert len(balances) == 1
        assert balances[0].account_id == "test_account_001"
        assert balances[0].balance == 4559500

    async def test_returns_empty_for_user_without_accounts(self, session: AsyncSession, test_user: User):
        # User exists but has no accounts
        import uuid
        from src.models.user import User

        lonely_user = User(
            id=uuid.uuid4(),
            name="Lonely",
            email="lonely@example.com",
            password="hashed",
            is_active=True,
            is_superuser=False,
            is_admin=False,
            is_verified=True,
        )
        session.add(lonely_user)
        await session.flush()

        service = BalanceService(session)
        balances = await service.get_user_balances(lonely_user.id)
        assert balances == []


class TestGetUserBalanceSummary:

    async def test_summary_with_totals(
        self, session: AsyncSession, test_user: User, test_account, sample_transactions,
    ):
        service = BalanceService(session)
        summary = await service.get_user_balance_summary(test_user.id)

        assert len(summary.accounts) == 1
        assert 980 in summary.totals_by_currency
        assert summary.totals_by_currency[980] == 4559500


class TestGetBalanceHistory:

    async def test_daily_aggregation(
        self, session: AsyncSession, test_user: User, test_account, sample_transactions,
    ):
        base_time = 1711929600
        service = BalanceService(session)
        history = await service.get_balance_history(
            user_id=test_user.id,
            from_timestamp=base_time,
            to_timestamp=base_time + 86400 * 3,
            account_id=test_account.account_id,
        )

        assert len(history) == 3  # 3 days

        # Day 1: income 5000000, expenses 150000+45000=195000
        day1 = history[0]
        assert day1.income == 5000000
        assert day1.expenses == 195000
        assert day1.net == 5000000 - 195000
        assert day1.transaction_count == 3

        # Day 2: no income, expenses 2500+18000=20500
        day2 = history[1]
        assert day2.income == 0
        assert day2.expenses == 20500
        assert day2.transaction_count == 2

        # Day 3: income 5000, expenses 230000
        day3 = history[2]
        assert day3.income == 5000
        assert day3.expenses == 230000
        assert day3.transaction_count == 2

    async def test_empty_period(
        self, session: AsyncSession, test_user: User, test_account, sample_transactions,
    ):
        service = BalanceService(session)
        history = await service.get_balance_history(
            user_id=test_user.id,
            from_timestamp=0,
            to_timestamp=100,
        )
        assert history == []


class TestGetIncomeVsExpenses:

    async def test_totals_for_period(
        self, session: AsyncSession, test_user: User, test_account, sample_transactions,
    ):
        base_time = 1711929600
        service = BalanceService(session)
        result = await service.get_income_vs_expenses(
            user_id=test_user.id,
            from_timestamp=base_time,
            to_timestamp=base_time + 86400 * 3,
        )

        # Total income: 5000000 + 5000 = 5005000
        assert result.total_income == 5005000
        # Total expenses: 150000 + 45000 + 2500 + 18000 + 230000 = 445500
        assert result.total_expenses == 445500
        assert result.net_savings == 5005000 - 445500
        assert result.savings_rate is not None
        assert result.savings_rate == round((5005000 - 445500) / 5005000 * 100, 2)

    async def test_zero_income_no_savings_rate(
        self, session: AsyncSession, test_user: User, test_account, sample_transactions,
    ):
        base_time = 1711929600
        service = BalanceService(session)
        # Day 2 only: no income, only expenses
        result = await service.get_income_vs_expenses(
            user_id=test_user.id,
            from_timestamp=base_time + 86400,
            to_timestamp=base_time + 86400 * 2,
        )

        assert result.total_income == 0
        assert result.savings_rate is None


class TestGetSpendingByCategory:

    async def test_category_breakdown(
        self, session: AsyncSession, test_user: User, test_account,
        sample_transactions, seed_mcc_categories,
    ):
        base_time = 1711929600
        service = BalanceService(session)
        categories = await service.get_spending_by_category(
            user_id=test_user.id,
            from_timestamp=base_time,
            to_timestamp=base_time + 86400 * 3,
        )

        # Should have: groceries (150000+230000=380000), restaurants (45000),
        # fast_food (18000), transport (2500)
        cat_map = {c.category_name: c for c in categories}

        assert "groceries" in cat_map
        assert cat_map["groceries"].total_amount == 380000
        assert cat_map["groceries"].transaction_count == 2

        assert "restaurants" in cat_map
        assert cat_map["restaurants"].total_amount == 45000

        assert "fast_food" in cat_map
        assert cat_map["fast_food"].total_amount == 18000

        assert "transport" in cat_map
        assert cat_map["transport"].total_amount == 2500

        # Percentages should sum to ~100%
        total_pct = sum(c.percentage for c in categories)
        assert abs(total_pct - 100.0) < 0.1

    async def test_excludes_income_from_categories(
        self, session: AsyncSession, test_user: User, test_account,
        sample_transactions, seed_mcc_categories,
    ):
        base_time = 1711929600
        service = BalanceService(session)
        categories = await service.get_spending_by_category(
            user_id=test_user.id,
            from_timestamp=base_time,
            to_timestamp=base_time + 86400 * 3,
        )

        # MCC 6012 (financial/income) should not appear since we only count amount < 0
        cat_names = [c.category_name for c in categories]
        assert "financial" not in cat_names
