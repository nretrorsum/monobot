"""Одноразовий скрипт: створює юзера, прив'язує Monobank accounts, реєструє webhook."""

import asyncio
import os
import sys
from pathlib import Path

import httpx
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.config import async_session
from src.models.user import User
from src.models.account import UserAccount

MONO_TOKEN = os.getenv("MONO_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not MONO_TOKEN or not WEBHOOK_URL:
    print("Error: MONO_TOKEN and WEBHOOK_URL environment variables are required.")
    print("Usage: MONO_TOKEN=xxx WEBHOOK_URL=https://... python -m src.scripts.setup_real_account")
    sys.exit(1)


async def seed():
    client_info = httpx.get(
        "https://api.monobank.ua/personal/client-info",
        headers={"X-Token": MONO_TOKEN},
    ).json()

    name = client_info["name"]
    accounts = client_info["accounts"]
    print(f"Monobank user: {name}, accounts: {len(accounts)}")

    async with async_session() as session:
        # Створюємо або знаходимо юзера
        result = await session.execute(
            select(User).where(User.name == name)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                name=name,
                email=f"{name.replace(' ', '.').lower()}@monobot.local",
                password=None,
                is_active=True,
                is_superuser=False,
                is_admin=False,
                is_verified=False,
            )
            session.add(user)
            await session.flush()
            print(f"  Created user: {user.id}")
        else:
            print(f"  User exists: {user.id}")

        # Прив'язуємо accounts
        for acc in accounts:
            acc_id = acc["id"]
            result = await session.execute(
                select(UserAccount).where(UserAccount.account_id == acc_id)
            )
            if not result.scalar_one_or_none():
                session.add(UserAccount(user_id=user.id, account_id=acc_id))
                print(f"  Linked account: {acc_id} ({acc['type']}, currency={acc['currencyCode']})")
            else:
                print(f"  Account already linked: {acc_id}")

        await session.commit()

    # Реєструємо webhook
    resp = httpx.post(
        "https://api.monobank.ua/personal/webhook",
        headers={"X-Token": MONO_TOKEN, "Content-Type": "application/json"},
        json={"webHookUrl": WEBHOOK_URL},
    )
    if resp.status_code == 200:
        print(f"\n  Webhook registered: {WEBHOOK_URL}")
    else:
        print(f"\n  Webhook registration failed: {resp.status_code} {resp.text}")

    print("\nDone! Now make a transaction in Monobank to test.")


if __name__ == "__main__":
    asyncio.run(seed())