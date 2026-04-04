import calendar
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_session
from src.core.dependencies import CurrentUser
from src.schemas.balance import (
    AccountBalanceResponse,
    BurnRateResponse,
    CategorySpendingResponse,
    DailySummaryResponse,
    IncomeVsExpensesResponse,
    UserBalanceSummary,
)
from src.services.balance import BalanceService

balance_router = APIRouter(prefix="/balance", tags=["balance"])


def _date_to_timestamp(d: date) -> int:
    return int(calendar.timegm(d.timetuple()))


def _default_period() -> tuple[date, date]:
    today = date.today()
    from_date = today.replace(day=1)
    to_date = today
    return from_date, to_date


@balance_router.get("/")
async def get_balance_summary(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> UserBalanceSummary:
    service = BalanceService(session)
    return await service.get_user_balance_summary(user.id)


@balance_router.get("/accounts/{account_id}")
async def get_account_balance(
    account_id: str,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> AccountBalanceResponse:
    service = BalanceService(session)
    result = await service.get_current_balance(account_id)
    if not result:
        raise HTTPException(status_code=404, detail="Account not found")
    return result


@balance_router.get("/history")
async def get_balance_history(
    user: CurrentUser,
    account_id: str | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> list[DailySummaryResponse]:
    default_from, default_to = _default_period()
    from_ts = _date_to_timestamp(from_date or default_from)
    to_ts = _date_to_timestamp(to_date or default_to) + 86400  # include end date

    service = BalanceService(session)
    return await service.get_balance_history(user.id, from_ts, to_ts, account_id)


@balance_router.get("/income-expenses")
async def get_income_vs_expenses(
    user: CurrentUser,
    account_id: str | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> IncomeVsExpensesResponse:
    default_from, default_to = _default_period()
    from_ts = _date_to_timestamp(from_date or default_from)
    to_ts = _date_to_timestamp(to_date or default_to) + 86400

    service = BalanceService(session)
    return await service.get_income_vs_expenses(user.id, from_ts, to_ts, account_id)


@balance_router.get("/burn-rate")
async def get_burn_rate(
    user: CurrentUser,
    account_id: str | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> BurnRateResponse:
    default_from, default_to = _default_period()
    from_ts = _date_to_timestamp(from_date or default_from)
    to_ts = _date_to_timestamp(to_date or default_to) + 86400

    service = BalanceService(session)
    return await service.get_burn_rate(user.id, from_ts, to_ts, account_id)


@balance_router.get("/categories")
async def get_spending_by_category(
    user: CurrentUser,
    account_id: str | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> list[CategorySpendingResponse]:
    default_from, default_to = _default_period()
    from_ts = _date_to_timestamp(from_date or default_from)
    to_ts = _date_to_timestamp(to_date or default_to) + 86400

    service = BalanceService(session)
    return await service.get_spending_by_category(user.id, from_ts, to_ts, account_id)
