import uuid

from sqlalchemy import ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseUuidModel


class UserAccount(BaseUuidModel):
    __tablename__ = "user_account"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), index=True)
    account_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    currency_code: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    account_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)