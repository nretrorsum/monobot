import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import Base
from src.models import *  # noqa: F401, F403
from src.models.account import UserAccount
from src.models.mcc_category import MccCategory
from src.models.transaction import UserTransaction
from src.models.user import User


TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://monobot:monobot@localhost:5432/monobot_test",
)


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    """Provide a fresh engine + session per test to avoid asyncpg event loop issues."""
    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as session:
        yield session
        await session.close()

    # Clean up all data
    async with engine.begin() as conn:
        table_names = ", ".join(
            f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables)
        )
        await conn.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))

    await engine.dispose()


@pytest_asyncio.fixture
async def test_user(session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        name="Test User",
        email="test@example.com",
        password="hashed_password",
        is_active=True,
        is_superuser=False,
        is_admin=False,
        is_verified=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_account(session: AsyncSession, test_user: User) -> UserAccount:
    account = UserAccount(
        user_id=test_user.id,
        account_id="test_account_001",
        currency_code=980,
        account_type="black",
        display_name="5375 **** 1234",
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


@pytest_asyncio.fixture
async def seed_mcc_categories(session: AsyncSession) -> list[MccCategory]:
    categories = [
        MccCategory(mcc_code=5411, category_name="groceries", category_group="needs", display_name_uk="Продукти"),
        MccCategory(mcc_code=5812, category_name="restaurants", category_group="wants", display_name_uk="Ресторани"),
        MccCategory(mcc_code=5814, category_name="fast_food", category_group="wants", display_name_uk="Фаст-фуд"),
        MccCategory(mcc_code=4111, category_name="transport", category_group="needs", display_name_uk="Транспорт"),
    ]
    for c in categories:
        session.add(c)
    await session.commit()
    return categories


@pytest_asyncio.fixture
async def sample_transactions(
    session: AsyncSession, test_user: User, test_account: UserAccount,
) -> list[UserTransaction]:
    base_time = 1711929600  # 2024-04-01 00:00:00 UTC

    transactions_data = [
        {"time": base_time, "amount": 5000000, "balance": 5000000, "mcc": 6012,
         "description": "Зарплата", "operation_amount": 5000000},
        {"time": base_time + 3600, "amount": -150000, "balance": 4850000, "mcc": 5411,
         "description": "АТБ", "operation_amount": 150000},
        {"time": base_time + 7200, "amount": -45000, "balance": 4805000, "mcc": 5812,
         "description": "Пузата Хата", "operation_amount": 45000},
        {"time": base_time + 86400, "amount": -2500, "balance": 4802500, "mcc": 4111,
         "description": "Метро", "operation_amount": 2500},
        {"time": base_time + 90000, "amount": -18000, "balance": 4784500, "mcc": 5814,
         "description": "МакДональдз", "operation_amount": 18000},
        {"time": base_time + 172800, "amount": -230000, "balance": 4554500, "mcc": 5411,
         "description": "Сільпо", "operation_amount": 230000},
        {"time": base_time + 176400, "amount": 5000, "balance": 4559500, "mcc": 6012,
         "description": "Кешбек", "operation_amount": 5000},
    ]

    txs = []
    for i, data in enumerate(transactions_data):
        tx = UserTransaction(
            user_id=test_user.id,
            account_id=test_account.account_id,
            transaction_id=f"tx_{i:04d}",
            time=data["time"],
            description=data["description"],
            mcc=data["mcc"],
            original_mcc=data["mcc"],
            amount=data["amount"],
            operation_amount=data["operation_amount"],
            currency_code=980,
            commission_rate=0,
            cashback_amount=0,
            balance=data["balance"],
            hold=False,
        )
        session.add(tx)
        txs.append(tx)

    await session.commit()
    return txs


@pytest_asyncio.fixture
async def extended_transactions(
    session: AsyncSession, test_user: User, test_account: UserAccount,
) -> list[UserTransaction]:
    """Транзакції за 14 днів для тестування burn rate та ковзних середніх."""
    base_time = 1711929600  # 2024-04-01 00:00:00 UTC
    day = 86400

    # Витрати по дням (в копійках): різні суми для перевірки ковзних середніх
    daily_expenses = [
        # Тиждень 1 (дні 0-6): попередній період для тренду
        (0, -120000),   # день 0: 1200 грн
        (1, -80000),    # день 1: 800 грн
        (2, -150000),   # день 2: 1500 грн
        (3, 0),         # день 3: 0 (пропуск — день без витрат)
        (4, -200000),   # день 4: 2000 грн
        (5, -60000),    # день 5: 600 грн
        (6, -90000),    # день 6: 900 грн
        # Тиждень 2 (дні 7-13): основний період
        (7, -180000),   # день 7: 1800 грн
        (8, -50000),    # день 8: 500 грн
        (9, -300000),   # день 9: 3000 грн
        (10, -70000),   # день 10: 700 грн
        (11, 0),        # день 11: 0 (пропуск)
        (12, -110000),  # день 12: 1100 грн
        (13, -140000),  # день 13: 1400 грн
    ]

    txs = []
    balance = 10000000  # стартовий баланс 100 000 грн

    # Дохід на початку
    tx = UserTransaction(
        user_id=test_user.id,
        account_id=test_account.account_id,
        transaction_id="ext_income_001",
        time=base_time,
        description="Зарплата",
        mcc=6012,
        original_mcc=6012,
        amount=10000000,
        operation_amount=10000000,
        currency_code=980,
        commission_rate=0,
        cashback_amount=0,
        balance=balance,
        hold=False,
    )
    session.add(tx)
    txs.append(tx)

    for i, (day_offset, amount) in enumerate(daily_expenses):
        if amount == 0:
            continue
        balance += amount
        tx = UserTransaction(
            user_id=test_user.id,
            account_id=test_account.account_id,
            transaction_id=f"ext_tx_{i:04d}",
            time=base_time + day_offset * day + 43200,  # опівдні
            description=f"Витрата день {day_offset}",
            mcc=5411,
            original_mcc=5411,
            amount=amount,
            operation_amount=abs(amount),
            currency_code=980,
            commission_rate=0,
            cashback_amount=0,
            balance=balance,
            hold=False,
        )
        session.add(tx)
        txs.append(tx)

    await session.commit()
    return txs
