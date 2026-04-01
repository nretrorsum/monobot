import uuid

from sqlalchemy import ForeignKey, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseUuidModel


class UserToken(BaseUuidModel):
    __tablename__ = "user_token"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), unique=True, index=True)
    encrypted_token: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
