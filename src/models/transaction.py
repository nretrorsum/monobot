import uuid

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseUuidModel


class UserTransaction(BaseUuidModel):
    __tablename__ = "user_transaction"
    __table_args__ = (
        Index("ix_user_transaction_account_time", "account_id", "time"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), index=True)
    account_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("user_account.account_id"), index=True, nullable=True
    )
    transaction_id: Mapped[str] = mapped_column(String(64), unique=True)
    time: Mapped[int] = mapped_column(BigInteger, index=True)
    description: Mapped[str] = mapped_column(String(512))
    mcc: Mapped[int] = mapped_column(Integer)
    original_mcc: Mapped[int] = mapped_column(Integer)
    amount: Mapped[int] = mapped_column(BigInteger)
    operation_amount: Mapped[int] = mapped_column(BigInteger)
    currency_code: Mapped[int] = mapped_column(SmallInteger)
    commission_rate: Mapped[int] = mapped_column(BigInteger, default=0)
    cashback_amount: Mapped[int] = mapped_column(BigInteger, default=0)
    balance: Mapped[int] = mapped_column(BigInteger)
    hold: Mapped[bool] = mapped_column(Boolean, default=False)
    comment: Mapped[str] = mapped_column(String(512), nullable=True)
    receipt_id: Mapped[str] = mapped_column(String(128), nullable=True)
    counter_edrpou: Mapped[str] = mapped_column(String(32), nullable=True)
    counter_iban: Mapped[str] = mapped_column(String(64), nullable=True)
    counter_name: Mapped[str] = mapped_column(String(256), nullable=True)
