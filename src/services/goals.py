import datetime
from datetime import date, timedelta
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
)


class GoalsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # --- SpendingConfig ---

    async def get_spending_config(self, user_id: UUID) -> SpendingConfigResponse | None:
        result = await self.session.execute(
            select(SpendingConfig).where(SpendingConfig.user_id == user_id)
        )
        config = result.scalar_one_or_none()
        if not config:
            return None
        return SpendingConfigResponse.model_validate(config)

    async def upsert_spending_config(
        self, user_id: UUID, data: SpendingConfigCreate
    ) -> SpendingConfigResponse:
        result = await self.session.execute(
            select(SpendingConfig).where(SpendingConfig.user_id == user_id)
        )
        config = result.scalar_one_or_none()

        if config:
            config.daily_limit = data.daily_limit
        else:
            config = SpendingConfig(user_id=user_id, daily_limit=data.daily_limit)
            self.session.add(config)

        await self.session.commit()
        await self.session.refresh(config)
        return SpendingConfigResponse.model_validate(config)

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

        expenses_by_day = await self._fetch_daily_expenses(user_id, goal.created_at)
        return self._build_response(goal, config.daily_limit, expenses_by_day)

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

        earliest = min(g.created_at for g in goals)
        expenses_by_day = await self._fetch_daily_expenses(user_id, earliest)

        return [
            self._build_response(goal, config.daily_limit, expenses_by_day)
            for goal in goals
        ]

    async def get_goal(self, user_id: UUID, goal_id: UUID) -> SavingsGoalResponse:
        config = await self._require_spending_config(user_id)
        goal = await self._get_goal_or_404(user_id, goal_id)

        expenses_by_day = await self._fetch_daily_expenses(user_id, goal.created_at)
        return self._build_response(goal, config.daily_limit, expenses_by_day)

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

        expenses_by_day = await self._fetch_daily_expenses(user_id, goal.created_at)
        return self._build_response(goal, config.daily_limit, expenses_by_day)

    async def delete_goal(self, user_id: UUID, goal_id: UUID) -> None:
        goal = await self._get_goal_or_404(user_id, goal_id)
        await self.session.delete(goal)
        await self.session.commit()

    # --- Progress calculation ---

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

    def _build_response(
        self,
        goal: SavingsGoal,
        daily_limit: int,
        expenses_by_day: dict[date, int],
    ) -> SavingsGoalResponse:
        today = date.today()
        start_date = goal.created_at.date()
        total_days = max((today - start_date).days + 1, 1)

        # Calculate total saved
        total_saved_raw = 0
        for i in range(total_days):
            d = start_date + timedelta(days=i)
            actual_expenses = expenses_by_day.get(d, 0)
            total_saved_raw += daily_limit - actual_expenses

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
