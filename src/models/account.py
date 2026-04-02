import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseUuidModel


class UserAccount(BaseUuidModel):
    __tablename__ = "user_account"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), index=True)
    account_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)