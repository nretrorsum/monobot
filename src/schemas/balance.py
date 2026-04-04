from datetime import date

from pydantic import BaseModel, ConfigDict


class AccountBalanceResponse(BaseModel):
    account_id: str
    currency_code: int
    balance: int
    display_name: str | None
    last_transaction_time: int | None

    model_config = ConfigDict(from_attributes=True)


class UserBalanceSummary(BaseModel):
    accounts: list[AccountBalanceResponse]
    totals_by_currency: dict[int, int]


class DailySummaryResponse(BaseModel):
    date: date
    income: int
    expenses: int
    net: int
    closing_balance: int
    transaction_count: int


class BalanceHistoryResponse(BaseModel):
    account_id: str | None
    currency_code: int
    data: list[DailySummaryResponse]


class CategorySpendingResponse(BaseModel):
    category_name: str
    display_name: str
    total_amount: int
    transaction_count: int
    percentage: float


class IncomeVsExpensesResponse(BaseModel):
    period_start: date
    period_end: date
    total_income: int
    total_expenses: int
    net_savings: int
    savings_rate: float | None


class DailyExpensesItem(BaseModel):
    date: date
    expenses: int
    moving_avg_7d: int | None


class BurnRateResponse(BaseModel):
    period_start: date
    period_end: date
    total_expenses: int
    days_in_period: int
    avg_daily_expenses: int
    moving_avg_7d: int | None
    moving_avg_30d: int | None
    prev_period_avg_daily: int | None
    trend_percentage: float | None
    daily_breakdown: list[DailyExpensesItem]
