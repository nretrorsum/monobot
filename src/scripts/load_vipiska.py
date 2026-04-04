"""Завантажує транзакції з vipiska.json в БД."""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select, update

from src.core.config import async_session
from src.models.transaction import UserTransaction

VIPISKA_PATH = Path(__file__).parent / "vipiska.json"
USER_ID = UUID("6e6d0b44-4c36-4880-a01c-05a5e8835fc0")
ACCOUNT_ID = "jasBTCYAxgpexy6pRBC_uA"


async def load():
    with open(VIPISKA_PATH) as f:
        transactions = json.load(f)

    print(f"Знайдено {len(transactions)} транзакцій у vipiska.json")

    async with async_session() as session:
        # Перевіряємо які transaction_id вже є в БД
        existing = await session.execute(
            select(UserTransaction.transaction_id).where(
                UserTransaction.user_id == USER_ID
            )
        )
        existing_ids = {row[0] for row in existing.all()}
        print(f"Вже в БД: {len(existing_ids)} транзакцій")

        added = 0
        skipped = 0
        for tx_data in transactions:
            tx_id = tx_data["id"]
            if tx_id in existing_ids:
                skipped += 1
                continue

            real_dt = datetime.fromtimestamp(tx_data["time"], tz=timezone.utc)
            tx = UserTransaction(
                user_id=USER_ID,
                account_id=ACCOUNT_ID,
                transaction_id=tx_id,
                time=tx_data["time"],
                description=tx_data["description"],
                mcc=tx_data["mcc"],
                original_mcc=tx_data["originalMcc"],
                amount=tx_data["amount"],
                operation_amount=tx_data["operationAmount"],
                currency_code=tx_data["currencyCode"],
                commission_rate=tx_data.get("commissionRate", 0),
                cashback_amount=tx_data.get("cashbackAmount", 0),
                balance=tx_data["balance"],
                hold=tx_data.get("hold", False),
                receipt_id=tx_data.get("receiptId"),
                comment=tx_data.get("comment"),
                counter_edrpou=tx_data.get("counterEdrpou"),
                counter_iban=tx_data.get("counterIban"),
                counter_name=tx_data.get("counterName"),
                created_at=real_dt,
                updated_at=real_dt,
            )
            session.add(tx)
            added += 1

        await session.commit()
        print(f"Додано: {added}, пропущено (дублі): {skipped}")

        # Оновлюємо created_at/updated_at для вже існуючих записів
        if skipped > 0:
            print("Оновлюю created_at для існуючих записів...")
            for tx_data in transactions:
                if tx_data["id"] in existing_ids:
                    real_dt = datetime.fromtimestamp(tx_data["time"], tz=timezone.utc)
                    await session.execute(
                        update(UserTransaction)
                        .where(UserTransaction.transaction_id == tx_data["id"])
                        .values(created_at=real_dt, updated_at=real_dt)
                    )
            await session.commit()
            print(f"Оновлено: {skipped} записів")


if __name__ == "__main__":
    asyncio.run(load())
