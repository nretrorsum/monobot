from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TokenCreate(BaseModel):
    user_id: UUID
    token: str


class TokenResponse(BaseModel):
    user_id: UUID
    created_at: datetime
