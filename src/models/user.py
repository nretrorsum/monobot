from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseUuidModel


class User(BaseUuidModel):
    __tablename__ = "user"

    name: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean)
    is_superuser: Mapped[bool] = mapped_column(Boolean)
    is_admin: Mapped[bool] = mapped_column(Boolean)
    is_verified: Mapped[bool] = mapped_column(Boolean)