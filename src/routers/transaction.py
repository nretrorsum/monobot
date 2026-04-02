import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import DEBUG, get_session
from src.core.webhook_verify import verify_webhook_signature
from src.schemas.transaction import WebhookPayload
from src.services.transaction import TransactionService

logger = logging.getLogger(__name__)

transaction_router = APIRouter(
    prefix="/transaction",
)


@transaction_router.get("/webhook")
async def verify_webhook():
    logger.info("Monobank webhook verification request received")
    return Response(status_code=200)


@transaction_router.post("/webhook")
async def create_transaction(
        request: Request,
        session: AsyncSession = Depends(get_session),
        x_sign: str | None = Header(None, alias="X-Sign"),
    ) -> dict:
        body = await request.body()

        if not DEBUG:
            if not x_sign:
                raise HTTPException(status_code=400, detail="Missing X-Sign header")
            if not await verify_webhook_signature(body, x_sign):
                raise HTTPException(status_code=400, detail="Invalid webhook signature")

        transaction_data = WebhookPayload.model_validate_json(body)
        account_id = transaction_data.data.account
        item = transaction_data.data.statement_item
        logger.info("Webhook received: account=%s, transaction_id=%s, amount=%s",
                     account_id, item.transaction_id, item.amount)

        service = TransactionService(session)
        user_id = await service.get_user_id_by_account(account_id)
        if not user_id:
            logger.warning("Unknown account: %s", account_id)
            raise HTTPException(status_code=404, detail="Account not linked to any user")

        logger.info("Account %s resolved to user %s", account_id, user_id)
        await service.create_transaction(item, user_id=user_id)
        logger.info("Transaction %s saved for user %s", item.transaction_id, user_id)
        return {"status": "success"}
