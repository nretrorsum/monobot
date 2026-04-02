from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseUuidModel


class MccCategory(BaseUuidModel):
    __tablename__ = "mcc_category"

    mcc_code: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    category_name: Mapped[str] = mapped_column(String(64))
    category_group: Mapped[str] = mapped_column(String(32))
    display_name_uk: Mapped[str] = mapped_column(String(128))
