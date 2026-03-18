from src.database.models import BaseUuidModel

from sqlalchemy import DateTime, func, String
from sqlalchemy.orm import Mapped, mapped_column

class User(BaseUuidModel):
    name: Mapped[str] = String(max_length=255, unique=True)
    email: Mapped[str] = String(max_length=255, unique=True)
    password: Mapped[str] = String(max_length=255)
