import uuid
import logging

from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.transaction import StatementItem
from src.models.account import UserAccount
from src.models.transaction import UserTransaction

logger = logging.getLogger(__name__)

class TransactionService:

    def __init__(self, session):
        self.session: AsyncSession = session

    async def get_user_id_by_account(self, account_id: str) -> uuid.UUID | None:
        result = await self.session.execute(
            select(UserAccount.user_id).where(UserAccount.account_id == account_id)
        )
        return result.scalar_one_or_none()

    async def _save_inexistent_account(self, account_id: str, user_id: uuid.UUID, user_transaction: StatementItem) -> str | None:
        result = await self.session.execute(
            select(exists().where(UserAccount.account_id == account_id))
        )
        account_exists = result.scalar()

        if not account_exists:
            try:
                user_account = UserAccount(
                    user_id=user_id,
                    account_id=account_id,
                    currency_code=user_transaction.currency_code,
                )
                self.session.add(user_account)
                await self.session.commit()
                await self.session.refresh(user_account)
                return user_account.account_id
            except Exception as e:
                await self.session.rollback()
                logger.error(f"Error while saving unexistent account:{e}")
        return account_id

    async def create_transaction(
        self, data: StatementItem, user_id: uuid.UUID | None, account_id: str | None = None,
    ) -> UserTransaction:
        transaction = UserTransaction(
            transaction_id=data.transaction_id,
            user_id=user_id if user_id else None,
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
