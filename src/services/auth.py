import logging
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import encrypt_token, decrypt_token
from src.models.auth import UserToken

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
                return existing

            token = UserToken(
                user_id=user_id,
                encrypted_token=encrypt_token(raw_token),
            )
            self.session.add(token)
            await self.session.commit()
            await self.session.refresh(token)
            return token
        except IntegrityError as e:
            await self.session.rollback()
            logger.error("User %s not found: %s", user_id, e)
            raise ValueError(f"User {user_id} does not exist") from e
        except Exception:
            await self.session.rollback()
            logger.exception("Error saving token for user %s", user_id)
            raise

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
