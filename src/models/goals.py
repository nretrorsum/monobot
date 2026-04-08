import enum
import uuid
from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseUuidModel


class GoalStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class SpendingConfig(BaseUuidModel):
    __tablename__ = "spending_config"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), unique=True, index=True)
    daily_limit: Mapped[int] = mapped_column(BigInteger)  # kopecks
    income_day: Mapped[int] = mapped_column(SmallInteger, nullable=True)  # 1-31, day of month when salary arrives
    income_window: Mapped[int] = mapped_column(SmallInteger, default=3, nullable=True)  # ±days tolerance
    set_income: Mapped[int] = mapped_column(BigInteger, nullable=True)


class SavingsGoal(BaseUuidModel):
    __tablename__ = "savings_goal"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    target_amount: Mapped[int] = mapped_column(BigInteger)  # kopecks
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=GoalStatus.active.value)
    allocation_percent: Mapped[int] = mapped_column(SmallInteger, default=100)  # 1-100
