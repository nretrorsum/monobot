import calendar
import datetime
from datetime import date, timedelta
import logging
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.goals import GoalStatus, SavingsGoal, SpendingConfig
from src.models.transaction import UserTransaction
from src.schemas.goals import (
    SavingsGoalCreate,
    SavingsGoalResponse,
    SavingsGoalUpdate,
    SpendingConfigCreate,
    SpendingConfigResponse,
    UpdateSpendingSum, UpdateSetIncome,
)

logger = logging.getLogger(__name__)


class GoalsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # --- SpendingConfig ---

    async def get_spending_config(self, user_id: UUID) -> SpendingConfigResponse | None:
        config = await self._get_spending_config_model(user_id)
        if not config:
            return None
        return await self._build_config_response(user_id, config)

    async def upsert_daily_limit(
        self, user_id: UUID, data: UpdateSpendingSum,
    ) -> SpendingConfigResponse:
        config = await self._get_spending_config_model(user_id)
        if config:
            config.daily_limit = data.daily_limit
        else:
            raise HTTPException(status_code=404, detail="Config not found")
        await self.session.commit()
        await self.session.refresh(config)
        return await self._build_config_response(user_id, config)

    async def upsert_set_income(
        self, user_id: UUID, data: UpdateSetIncome,
    ) -> SpendingConfigResponse:
        config = await self._get_spending_config_model(user_id)
        if config:
            config.set_income = data.set_income
        else:
            raise HTTPException(status_code=404, detail="Config not found")
        await self.session.commit()
        await self.session.refresh(config)
        return await self._build_config_response(user_id, config)

    async def upsert_spending_config(
        self, user_id: UUID, data: SpendingConfigCreate
    ) -> SpendingConfigResponse:
        result = await self.session.execute(
            select(SpendingConfig).where(SpendingConfig.user_id == user_id)
        )
        config = result.scalar_one_or_none()

        if config:
            config.daily_limit = data.daily_limit
            config.income_day = data.income_day
            config.income_window = data.income_window
        else:
            config = SpendingConfig(
                user_id=user_id,
                daily_limit=data.daily_limit,
                income_day=data.income_day,
                income_window=data.income_window,
                set_income=data.set_income,
            )
            self.session.add(config)

        await self.session.commit()
        await self.session.refresh(config)
        return await self._build_config_response(user_id, config)

    async def _build_config_response(
        self, user_id: UUID, config: SpendingConfig
    ) -> SpendingConfigResponse:
        salary = await self._detect_salary(user_id, config.income_day, config.income_window)

        detected_income = None
        detected_income_date = None
        daily_budget = None
        planned_daily_savings = None
        planned_monthly_savings = None

        if salary:
            detected_income, detected_income_date = salary
            today = date.today()
            days_in_month = calendar.monthrange(today.year, today.month)[1]
            # logger.info(f"Found {days_in_month} days in month {today.month}")
            daily_budget = detected_income // days_in_month
            # logger.info(f"Found {daily_budget} days in month {today.month}")
            planned_daily_savings = daily_budget - config.daily_limit
            # logger.info(f"Found {planned_daily_savings} days planned")
            planned_monthly_savings = planned_daily_savings * days_in_month

        return SpendingConfigResponse(
            id=config.id,
            daily_limit=config.daily_limit,
            income_day=config.income_day,
            income_window=config.income_window,
            created_at=config.created_at,
            updated_at=config.updated_at,
            detected_income=detected_income,
            detected_income_date=detected_income_date,
            daily_budget=daily_budget,
            planned_daily_savings=planned_daily_savings,
            planned_monthly_savings=planned_monthly_savings,
        )

    # --- SavingsGoal CRUD ---

    async def create_goal(
        self, user_id: UUID, data: SavingsGoalCreate
    ) -> SavingsGoalResponse:
        config = await self._require_spending_config(user_id)
        await self._validate_allocation(user_id, data.allocation_percent)

        goal = SavingsGoal(
            user_id=user_id,
            name=data.name,
            target_amount=data.target_amount,
            deadline=data.deadline,
            allocation_percent=data.allocation_percent,
        )
        self.session.add(goal)
        await self.session.commit()
        await self.session.refresh(goal)

        salary = await self._detect_salary(user_id, config.income_day, config.income_window)
        expenses_by_day = await self._fetch_daily_expenses(user_id, goal.created_at)
        return self._build_response(goal, config, salary, expenses_by_day)

    async def get_goals(self, user_id: UUID) -> list[SavingsGoalResponse]:
        config = await self._get_spending_config_model(user_id)
        if not config:
            return []

        result = await self.session.execute(
            select(SavingsGoal)
            .where(SavingsGoal.user_id == user_id)
            .order_by(SavingsGoal.created_at.desc())
        )
        goals = result.scalars().all()
        if not goals:
            return []

        salary = await self._detect_salary(user_id, config.income_day, config.income_window)
        earliest = min(g.created_at for g in goals)
        expenses_by_day = await self._fetch_daily_expenses(user_id, earliest)

        return [
            self._build_response(goal, config, salary, expenses_by_day)
            for goal in goals
        ]

    async def get_goal(self, user_id: UUID, goal_id: UUID) -> SavingsGoalResponse:
        config = await self._require_spending_config(user_id)
        goal = await self._get_goal_or_404(user_id, goal_id)

        salary = await self._detect_salary(user_id, config.income_day, config.income_window)
        expenses_by_day = await self._fetch_daily_expenses(user_id, goal.created_at)
        return self._build_response(goal, config, salary, expenses_by_day)

    async def update_goal(
        self, user_id: UUID, goal_id: UUID, data: SavingsGoalUpdate
    ) -> SavingsGoalResponse:
        config = await self._require_spending_config(user_id)
        goal = await self._get_goal_or_404(user_id, goal_id)

        if data.allocation_percent is not None:
            await self._validate_allocation(
                user_id, data.allocation_percent, exclude_goal_id=goal_id
            )
            goal.allocation_percent = data.allocation_percent

        if data.name is not None:
            goal.name = data.name
        if data.target_amount is not None:
            goal.target_amount = data.target_amount
        if data.deadline is not None:
            goal.deadline = data.deadline
        if data.status is not None:
            if data.status not in [s.value for s in GoalStatus]:
                raise HTTPException(400, f"Invalid status: {data.status}")
            goal.status = data.status

        await self.session.commit()
        await self.session.refresh(goal)

        salary = await self._detect_salary(user_id, config.income_day, config.income_window)
        expenses_by_day = await self._fetch_daily_expenses(user_id, goal.created_at)
        return self._build_response(goal, config, salary, expenses_by_day)

    async def delete_goal(self, user_id: UUID, goal_id: UUID) -> None:
        goal = await self._get_goal_or_404(user_id, goal_id)
        await self.session.delete(goal)
        await self.session.commit()

    # --- Salary detection ---

    async def _detect_salary(
        self, user_id: UUID, income_day: int, window: int
    ) -> tuple[int, date | None] | None:
        """Find the largest positive transaction near income_day ±window for the current budget period."""
        user_income = await self._get_spending_config_model(user_id)

        if user_income.set_income:
            return (int(user_income.set_income), None)

        today = date.today()

        # Determine which month's salary to look for
        if today.day >= income_day - window:
            ref_year, ref_month = today.year, today.month
        else:
            # Look in previous month
            first_of_current = today.replace(day=1)
            prev = first_of_current - timedelta(days=1)
            ref_year, ref_month = prev.year, prev.month

        # Clamp income_day to actual days in that month
        max_day = calendar.monthrange(ref_year, ref_month)[1]
        clamped_day = min(income_day, max_day)
        center = date(ref_year, ref_month, clamped_day)

        window_start = center - timedelta(days=window)
        window_end = center + timedelta(days=window)

        from_ts = int(datetime.datetime.combine(
            window_start, datetime.time.min, tzinfo=datetime.timezone.utc
        ).timestamp())
        to_ts = int(datetime.datetime.combine(
            window_end, datetime.time.max, tzinfo=datetime.timezone.utc
        ).timestamp())

        # Largest positive transaction in window
        query = (
            select(UserTransaction.amount, UserTransaction.time)
            .where(
                UserTransaction.user_id == user_id,
                UserTransaction.amount > 0,
                UserTransaction.time >= from_ts,
                UserTransaction.time <= to_ts,
            )
            .order_by(UserTransaction.amount.desc())
            .limit(1)
        )

        result = await self.session.execute(query)
        row = result.first()

        if not row:
            return None

        tx_date = datetime.datetime.fromtimestamp(
            row.time, tz=datetime.timezone.utc
        ).date()
        return (row.amount, tx_date)

    # --- Daily expenses ---

    async def _fetch_daily_expenses(
        self, user_id: UUID, since: datetime.datetime
    ) -> dict[date, int]:
        start_of_day = datetime.datetime.combine(
            since.date(), datetime.time.min, tzinfo=datetime.timezone.utc
        )
        from_ts = int(start_of_day.timestamp())
        to_ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

        tx_date = func.date(func.to_timestamp(UserTransaction.time))

        query = (
            select(
                tx_date.label("day"),
                func.sum(func.abs(UserTransaction.amount)).label("expenses"),
            )
            .where(
                UserTransaction.user_id == user_id,
                UserTransaction.amount < 0,
                UserTransaction.time >= from_ts,
                UserTransaction.time <= to_ts,
            )
            .group_by(tx_date)
        )

        result = await self.session.execute(query)
        return {row.day: row.expenses for row in result.all()}

    # --- Progress calculation ---

    def _build_response(
        self,
        goal: SavingsGoal,
        config: SpendingConfig,
        salary: tuple[int, date | None] | None,
        expenses_by_day: dict[date, int],
    ) -> SavingsGoalResponse:
        today = date.today()
        start_date = goal.created_at.date()
        total_days = max((today - start_date).days + 1, 1)

        # Calculate daily_budget from detected salary
        if salary:
            monthly_income, _ = salary
            days_in_month = calendar.monthrange(today.year, today.month)[1]
            daily_budget = monthly_income // days_in_month
        else:
            # No salary detected — can't calculate real savings
            daily_budget = config.daily_limit  # fallback: assume budget = limit (0 savings)

        # Calculate total saved: daily_budget - actual_expenses per day
        total_saved_raw = 0
        for i in range(total_days):
            d = start_date + timedelta(days=i)
            actual_expenses = expenses_by_day.get(d, 0)
            total_saved_raw += daily_budget - actual_expenses

        current_saved = int(total_saved_raw * goal.allocation_percent / 100)
        daily_savings_rate = current_saved // total_days
        progress_percent = round(current_saved / goal.target_amount * 100, 2) if goal.target_amount > 0 else 0

        # Projected completion
        projected_completion = None
        if daily_savings_rate > 0:
            remaining = goal.target_amount - current_saved
            if remaining > 0:
                days_needed = remaining / daily_savings_rate
                projected_completion = today + timedelta(days=int(days_needed))

        # Deadline tracking
        on_track = None
        days_remaining = None
        shortfall_per_day = None

        if goal.deadline:
            days_remaining = (goal.deadline - today).days
            if current_saved >= goal.target_amount:
                on_track = True
            elif days_remaining > 0:
                on_track = (
                    projected_completion is not None
                    and projected_completion <= goal.deadline
                )
                if not on_track:
                    needed_per_day = (goal.target_amount - current_saved) // days_remaining
                    shortfall_per_day = max(0, needed_per_day - daily_savings_rate)
            else:
                on_track = False

        return SavingsGoalResponse(
            id=goal.id,
            name=goal.name,
            target_amount=goal.target_amount,
            deadline=goal.deadline,
            status=goal.status,
            allocation_percent=goal.allocation_percent,
            created_at=goal.created_at,
            current_saved=max(current_saved, 0),
            progress_percent=max(progress_percent, 0),
            daily_savings_rate=daily_savings_rate,
            projected_completion=projected_completion,
            on_track=on_track,
            days_remaining=days_remaining,
            shortfall_per_day=shortfall_per_day,
        )

    # --- Helpers ---

    async def _get_spending_config_model(self, user_id: UUID) -> SpendingConfig | None:
        result = await self.session.execute(
            select(SpendingConfig).where(SpendingConfig.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _require_spending_config(self, user_id: UUID) -> SpendingConfig:
        config = await self._get_spending_config_model(user_id)
        if not config:
            raise HTTPException(400, "Set spending config first (PUT /goals/config)")
        return config

    async def _get_goal_or_404(self, user_id: UUID, goal_id: UUID) -> SavingsGoal:
        result = await self.session.execute(
            select(SavingsGoal).where(
                SavingsGoal.id == goal_id, SavingsGoal.user_id == user_id
            )
        )
        goal = result.scalar_one_or_none()
        if not goal:
            raise HTTPException(404, "Goal not found")
        return goal

    async def _validate_allocation(
        self, user_id: UUID, new_percent: int, exclude_goal_id: UUID | None = None
    ) -> None:
        query = select(
            func.coalesce(func.sum(SavingsGoal.allocation_percent), 0)
        ).where(
            SavingsGoal.user_id == user_id,
            SavingsGoal.status == GoalStatus.active.value,
        )
        if exclude_goal_id:
            query = query.where(SavingsGoal.id != exclude_goal_id)

        result = await self.session.execute(query)
        current_sum = result.scalar_one()

        if current_sum + new_percent > 100:
            raise HTTPException(
                422,
                f"Total allocation would be {current_sum + new_percent}%, max is 100%",
            )