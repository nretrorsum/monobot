import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.transaction import StatementItem
from src.models.account import UserAccount
from src.models.transaction import UserTransaction


class TransactionService:

    def __init__(self, session):
        self.session: AsyncSession = session

    async def get_user_id_by_account(self, account_id: str) -> uuid.UUID | None:
        result = await self.session.execute(
            select(UserAccount.user_id).where(UserAccount.account_id == account_id)
        )
        return result.scalar_one_or_none()

    async def create_transaction(
        self, data: StatementItem, user_id, account_id: str | None = None,
    ) -> UserTransaction:
        transaction = UserTransaction(
            transaction_id=data.transaction_id,
            user_id=user_id,
            account_id=account_id,
            time=data.time,
            description=data.description,
            mcc=data.mcc,
            original_mcc=data.original_mcc,
            amount=data.amount,
            operation_amount=data.operation_amount,
            currency_code=data.currency_code,
            commission_rate=data.commission_rate,
            cashback_amount=data.cashback_amount,
            balance=data.balance,
            hold=data.hold,
            comment=data.comment,
            receipt_id=data.receipt_id,
            counter_edrpou=data.counter_edrpou,
            counter_iban=data.counter_iban,
            counter_name=data.counter_name,
        )
        self.session.add(transaction)
        await self.session.commit()
        await self.session.refresh(transaction)
        return transaction
