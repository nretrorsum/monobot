import logging
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import encrypt_token, decrypt_token
from src.core.mono_request import MonoRequestService
from src.models.auth import UserToken
from src.models.account import UserAccount

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_token(self, user_id: UUID, raw_token: str) -> UserToken:
        try:
            result = await self.session.execute(
                select(UserToken).where(UserToken.user_id == user_id)
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.encrypted_token = encrypt_token(raw_token)
                await self.session.commit()
                await self.session.refresh(existing)
            else:
                existing = UserToken(
                    user_id=user_id,
                    encrypted_token=encrypt_token(raw_token),
                )
                self.session.add(existing)
                await self.session.commit()
                await self.session.refresh(existing)

            await self._sync_mono_accounts(user_id, raw_token)
            return existing
        except IntegrityError as e:
            await self.session.rollback()
            logger.error("User %s not found: %s", user_id, e)
            raise ValueError(f"User {user_id} does not exist") from e
        except Exception:
            await self.session.rollback()
            logger.exception("Error saving token for user %s", user_id)
            raise

    async def _sync_mono_accounts(self, user_id: UUID, raw_token: str) -> None:
        try:
            async with MonoRequestService() as mono:
                client_info = await mono.get_client_info(raw_token)

            accounts = client_info.get("accounts", [])
            for acc in accounts:
                acc_id = acc["id"]
                result = await self.session.execute(
                    select(UserAccount).where(UserAccount.account_id == acc_id)
                )
                if not result.scalar_one_or_none():
                    self.session.add(UserAccount(user_id=user_id, account_id=acc_id))
                    logger.info("Linked account %s to user %s", acc_id, user_id)

            await self.session.commit()
            logger.info("Synced %d Monobank accounts for user %s", len(accounts), user_id)
        except Exception:
            logger.exception("Failed to sync Monobank accounts for user %s", user_id)
            await self.session.rollback()

    async def get_token(self, user_id: UUID) -> UserToken | None:
        result = await self.session.execute(
            select(UserToken).where(UserToken.user_id == user_id)
        )
        token = result.scalar_one_or_none()
        if token is None:
            return None
        return token

    async def delete_token(self, user_id: UUID) -> bool:
        result = await self.session.execute(
            delete(UserToken).where(UserToken.user_id == user_id)
        )
        await self.session.commit()
        return result.rowcount > 0
