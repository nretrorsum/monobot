from fastapi import FastAPI

from src.models import *  # noqa: F401, F403
from src.routers.transaction import transaction_router
from src.routers.auth import auth_router
from src.routers.jwt_auth import jwt_auth_router

app = FastAPI()

app.include_router(transaction_router)
app.include_router(auth_router)
app.include_router(jwt_auth_router, prefix="/auth", tags=["auth"])

@app.get("/health")
async def health():
    return {"status": "ok"}
