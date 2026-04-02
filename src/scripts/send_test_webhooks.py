"""
Скрипт для тестування вебхука Monobank локально.
Надсилає набір реалістичних транзакцій на локальний ендпоінт.

Перед надсиланням створює тестового користувача та прив'язує account_id в БД
(якщо вони ще не існують).

Використання:
    uv run python scripts/send_test_webhooks.py
    uv run python scripts/send_test_webhooks.py --url http://localhost:8000/transaction/webhook
    uv run python scripts/send_test_webhooks.py --index 2  # надіслати лише одну транзакцію
"""

import argparse
import asyncio
import sys
import time
import uuid
from pathlib import Path

import httpx
from sqlalchemy import select

# Додаємо корінь проєкту в sys.path для імпорту src.*
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

BASE_URL = "http://localhost:8000/transaction/webhook"
ACCOUNT_ID = "test_account_id_000"
TEST_USER_EMAIL = "test@example.com"

# amount у копійках, від'ємне — витрата, додатне — надходження
TRANSACTIONS = [
    {
        "id": uuid.uuid4().hex,
        "time": int(time.time()),
        "description": "АТБ-Маркет",
        "mcc": 5411,
        "originalMcc": 5411,
        "amount": -43250,
        "operationAmount": -43250,
        "currencyCode": 980,
        "commissionRate": 0,
        "cashbackAmount": 432,
        "balance": 1500000,
        "hold": True,
    },
    {
        "id": uuid.uuid4().hex,
        "time": int(time.time()),
        "description": "Bolt",
        "mcc": 4121,
        "originalMcc": 4121,
        "amount": -8900,
        "operationAmount": -8900,
        "currencyCode": 980,
        "commissionRate": 0,
        "cashbackAmount": 0,
        "balance": 1491100,
        "hold": True,
    },
    {
        "id": uuid.uuid4().hex,
        "time": int(time.time()),
        "description": "Пузата Хата",
        "mcc": 5812,
        "originalMcc": 5812,
        "amount": -21500,
        "operationAmount": -21500,
        "currencyCode": 980,
        "commissionRate": 0,
        "cashbackAmount": 215,
        "balance": 1469600,
        "hold": True,
    },
    {
        "id": uuid.uuid4().hex,
        "time": int(time.time()),
        "description": "ФОП Петренко",
        "mcc": 5999,
        "originalMcc": 5999,
        "amount": 5000000,
        "operationAmount": 5000000,
        "currencyCode": 980,
        "commissionRate": 0,
        "cashbackAmount": 0,
        "balance": 6469600,
        "hold": False,
        "comment": "Зарплата за березень",
    },
    {
        "id": uuid.uuid4().hex,
        "time": int(time.time()),
        "description": "Сільпо",
        "mcc": 5411,
        "originalMcc": 5411,
        "amount": -87430,
        "operationAmount": -87430,
        "currencyCode": 980,
        "commissionRate": 0,
        "cashbackAmount": 874,
        "balance": 6382170,
        "hold": True,
    },
    {
        "id": uuid.uuid4().hex,
        "time": int(time.time()),
        "description": "Netflix",
        "mcc": 4899,
        "originalMcc": 4899,
        "amount": -9990,
        "operationAmount": -399,
        "currencyCode": 840,
        "commissionRate": 0,
        "cashbackAmount": 0,
        "balance": 6372180,
        "hold": True,
    },
    {
        "id": uuid.uuid4().hex,
        "time": int(time.time()),
        "description": "ОККО",
        "mcc": 5541,
        "originalMcc": 5541,
        "amount": -185000,
        "operationAmount": -185000,
        "currencyCode": 980,
        "commissionRate": 0,
        "cashbackAmount": 1850,
        "balance": 6187180,
        "hold": True,
    },
    {
        "id": uuid.uuid4().hex,
        "time": int(time.time()),
        "description": "Аптека АНЦ",
        "mcc": 5912,
        "originalMcc": 5912,
        "amount": -35600,
        "operationAmount": -35600,
        "currencyCode": 980,
        "commissionRate": 0,
        "cashbackAmount": 356,
        "balance": 6151580,
        "hold": True,
    },
    {
        "id": uuid.uuid4().hex,
        "time": int(time.time()),
        "description": "Від Олени",
        "mcc": 4829,
        "originalMcc": 4829,
        "amount": 50000,
        "operationAmount": 50000,
        "currencyCode": 980,
        "commissionRate": 0,
        "cashbackAmount": 0,
        "balance": 6201580,
        "hold": False,
        "comment": "За вечерю",
    },
    {
        "id": uuid.uuid4().hex,
        "time": int(time.time()),
        "description": "Київстар",
        "mcc": 4814,
        "originalMcc": 4814,
        "amount": -25000,
        "operationAmount": -25000,
        "currencyCode": 980,
        "commissionRate": 0,
        "cashbackAmount": 0,
        "balance": 6176580,
        "hold": False,
    },
]


def build_webhook_payload(statement_item: dict) -> dict:
    return {
        "type": "StatementItem",
        "data": {
            "account": ACCOUNT_ID,
            "statementItem": statement_item,
        },
    }


def send_one(client: httpx.Client, url: str, tx: dict) -> None:
    payload = build_webhook_payload(tx)
    resp = client.post(url, json=payload)
    print(f'Response from server:{resp}')
    status = "OK" if resp.is_success else f"FAIL ({resp.status_code})"
    amount_uah = tx["amount"] / 100
    sign = "+" if amount_uah > 0 else ""
    print(f"  [{status}] {tx['description']:20s} {sign}{amount_uah:.2f} UAH")


async def seed_test_data():
    """Створює тестового користувача і прив'язує account_id, якщо ще не існують."""
    from src.core.config import async_session
    from src.models.user import User
    from src.models.account import UserAccount

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.email == TEST_USER_EMAIL)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                name="Test User",
                email=TEST_USER_EMAIL,
                password=None,
                is_active=True,
                is_superuser=False,
                is_admin=False,
                is_verified=False,
            )
            session.add(user)
            await session.flush()
            print(f"  Created test user: {user.id}")

        result = await session.execute(
            select(UserAccount).where(UserAccount.account_id == ACCOUNT_ID)
        )
        account = result.scalar_one_or_none()

        if not account:
            account = UserAccount(user_id=user.id, account_id=ACCOUNT_ID)
            session.add(account)
            print(f"  Linked account '{ACCOUNT_ID}' to user {user.id}")

        await session.commit()
        print(f"  Test user ready: {user.id}\n")


def main():
    parser = argparse.ArgumentParser(description="Send test Monobank webhooks")
    parser.add_argument("--url", default=BASE_URL, help="Webhook endpoint URL")
    parser.add_argument("--index", type=int, help="Send only one transaction by index (0-based)")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay between requests in seconds")
    parser.add_argument("--no-seed", action="store_true", help="Skip creating test user/account")
    args = parser.parse_args()

    if not args.no_seed:
        print("Seeding test data...")
        asyncio.run(seed_test_data())

    txs = [TRANSACTIONS[args.index]] if args.index is not None else TRANSACTIONS

    print(f"Sending {len(txs)} transaction(s) to {args.url}\n")

    with httpx.Client(timeout=10) as client:
        for tx in txs:
            send_one(client, args.url, tx)
            time.sleep(args.delay)

    print("\nDone!")


if __name__ == "__main__":
    main()