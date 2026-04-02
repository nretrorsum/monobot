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
