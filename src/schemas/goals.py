from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# --- SpendingConfig ---

class SpendingConfigCreate(BaseModel):
    daily_limit: int = Field(gt=0)
    income_day: int = Field(ge=1, le=31)
    income_window: int = Field(default=3, ge=1, le=7)


class SpendingConfigResponse(BaseModel):
    id: UUID
    daily_limit: int
    income_day: int
    income_window: int
    created_at: datetime
    updated_at: datetime

    # Dynamic fields (from salary detection)
    detected_income: int | None
    detected_income_date: date | None
    daily_budget: int | None
    planned_daily_savings: int | None
    planned_monthly_savings: int | None

    model_config = ConfigDict(from_attributes=True)


# --- SavingsGoal ---

class SavingsGoalCreate(BaseModel):
    name: str = Field(max_length=255)
    target_amount: int = Field(gt=0)
    deadline: date | None = None
    allocation_percent: int = Field(default=100, ge=1, le=100)


class SavingsGoalUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    target_amount: int | None = Field(default=None, gt=0)
    deadline: date | None = None
    allocation_percent: int | None = Field(default=None, ge=1, le=100)
    status: str | None = None


class SavingsGoalResponse(BaseModel):
    id: UUID
    name: str
    target_amount: int
    deadline: date | None
    status: str
    allocation_percent: int
    created_at: datetime

    # Dynamic fields
    current_saved: int
    progress_percent: float
    daily_savings_rate: int
    projected_completion: date | None
    on_track: bool | None
    days_remaining: int | None
    shortfall_per_day: int | None

    model_config = ConfigDict(from_attributes=True)