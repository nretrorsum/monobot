from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_session
from src.core.dependencies import CurrentUser
from src.schemas.goals import (
    SavingsGoalCreate,
    SavingsGoalResponse,
    SavingsGoalUpdate,
    SpendingConfigCreate,
    SpendingConfigResponse,
)
from src.services.goals import GoalsService

goals_router = APIRouter(prefix="/goals", tags=["goals"])


# --- SpendingConfig ---

@goals_router.get("/config")
async def get_spending_config(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> SpendingConfigResponse | None:
    service = GoalsService(session)
    return await service.get_spending_config(user.id)


@goals_router.put("/config")
async def upsert_spending_config(
    data: SpendingConfigCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> SpendingConfigResponse:
    service = GoalsService(session)
    return await service.upsert_spending_config(user.id, data)


# --- SavingsGoal ---

@goals_router.post("/")
async def create_goal(
    data: SavingsGoalCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> SavingsGoalResponse:
    service = GoalsService(session)
    return await service.create_goal(user.id, data)


@goals_router.get("/")
async def get_goals(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[SavingsGoalResponse]:
    service = GoalsService(session)
    return await service.get_goals(user.id)


@goals_router.get("/{goal_id}")
async def get_goal(
    goal_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> SavingsGoalResponse:
    service = GoalsService(session)
    return await service.get_goal(user.id, goal_id)


@goals_router.patch("/{goal_id}")
async def update_goal(
    goal_id: UUID,
    data: SavingsGoalUpdate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> SavingsGoalResponse:
    service = GoalsService(session)
    return await service.update_goal(user.id, goal_id, data)


@goals_router.delete("/{goal_id}", status_code=204)
async def delete_goal(
    goal_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> None:
    service = GoalsService(session)
    await service.delete_goal(user.id, goal_id)
