from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_session
from src.schemas.transaction import WebhookPayload
from src.services.transaction import TransactionService

transaction_router = APIRouter(
    prefix="/transaction",
)


@transaction_router.post("/webhook")
async def create_transaction(
        user_id: UUID,
        transaction_data: WebhookPayload,
        session: AsyncSession = Depends(get_session),
    ) -> dict:
        try:
            service = TransactionService(session)
            await service.create_transaction(transaction_data.data.statement_item, user_id=user_id)
            return {
                "status": "success"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
