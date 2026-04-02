from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import config
from src.core.logging import setup_logging
from src.models import *  # noqa: F401, F403

setup_logging()
from src.routers.transaction import transaction_router
from src.routers.auth import auth_router
from src.routers.jwt_auth import jwt_auth_router

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    docs_url="/docs" if config.DEBUG else None,
    redoc_url="/redoc" if config.DEBUG else None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

if config.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(transaction_router)
app.include_router(auth_router)
app.include_router(jwt_auth_router, prefix="/auth", tags=["auth"])


@app.get("/health")
async def health(db: AsyncSession = Depends(config.get_session)):
    result = {"status": "ok", "db": "ok", "redis": "ok"}
    status_code = 200

    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        result["db"] = "error"
        result["status"] = "degraded"
        status_code = 503

    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(config.REDIS_URL)
        await r.ping()
        await r.aclose()
    except Exception:
        result["redis"] = "error"
        result["status"] = "degraded"
        status_code = 503

    return JSONResponse(result, status_code=status_code)
