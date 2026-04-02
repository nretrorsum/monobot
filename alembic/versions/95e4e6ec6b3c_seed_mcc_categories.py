"""seed mcc categories

Revision ID: 95e4e6ec6b3c
Revises: b1200b9bef75
Create Date: 2026-04-02 23:39:11.117975

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '95e4e6ec6b3c'
down_revision: Union[str, None] = 'b1200b9bef75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    mcc_category = sa.table(
        "mcc_category",
        sa.column("id", sa.Uuid),
        sa.column("mcc_code", sa.Integer),
        sa.column("category_name", sa.String),
        sa.column("category_group", sa.String),
        sa.column("display_name_uk", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )

    import uuid
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    categories = [
        # Продукти та супермаркети
        (5411, "groceries", "needs", "Продукти / Супермаркети"),
        (5422, "groceries", "needs", "М'ясо / Риба"),
        (5441, "groceries", "needs", "Кондитерські"),
        (5451, "groceries", "needs", "Молочні продукти"),
        (5462, "groceries", "needs", "Пекарні"),
        # Кафе та ресторани
        (5812, "restaurants", "wants", "Ресторани"),
        (5813, "bars", "wants", "Бари / Нічні клуби"),
        (5814, "fast_food", "wants", "Фаст-фуд"),
        # Транспорт
        (4111, "transport", "needs", "Громадський транспорт"),
        (4121, "transport", "needs", "Таксі"),
        (4131, "transport", "needs", "Автобуси"),
        (5541, "fuel", "needs", "АЗС / Паливо"),
        (5542, "fuel", "needs", "АЗС / Паливо"),
        # Комунальні послуги
        (4900, "utilities", "needs", "Комунальні послуги"),
        (4814, "telecom", "needs", "Телекомунікації"),
        (4899, "utilities", "needs", "Комунальні платежі"),
        # Здоров'я
        (5912, "pharmacy", "needs", "Аптеки"),
        (8011, "healthcare", "needs", "Медичні послуги"),
        (8021, "healthcare", "needs", "Стоматологія"),
        (8099, "healthcare", "needs", "Медичні послуги (інше)"),
        # Одяг та взуття
        (5611, "clothing", "wants", "Чоловічий одяг"),
        (5621, "clothing", "wants", "Жіночий одяг"),
        (5641, "clothing", "wants", "Дитячий одяг"),
        (5651, "clothing", "wants", "Одяг (загальне)"),
        (5661, "clothing", "wants", "Взуття"),
        # Розваги
        (7832, "entertainment", "wants", "Кінотеатри"),
        (7841, "entertainment", "wants", "Відео / DVD"),
        (7911, "entertainment", "wants", "Розваги / Танці"),
        (7922, "entertainment", "wants", "Театри / Концерти"),
        (7941, "entertainment", "wants", "Спорт / Клуби"),
        # Електроніка
        (5732, "electronics", "wants", "Електроніка"),
        (5734, "electronics", "wants", "Комп'ютери / ПЗ"),
        # Освіта
        (8211, "education", "needs", "Освіта / Школи"),
        (8220, "education", "needs", "Університети"),
        (8241, "education", "needs", "Дистанційна освіта"),
        # Краса
        (7230, "beauty", "wants", "Перукарні / Салони краси"),
        (7298, "beauty", "wants", "СПА / Масаж"),
        # Подорожі
        (3000, "travel", "wants", "Авіакомпанії"),
        (7011, "travel", "wants", "Готелі / Мотелі"),
        (4511, "travel", "wants", "Авіаквитки"),
        # Фінансові послуги
        (6012, "financial", "needs", "Банківські послуги"),
        (6011, "financial", "needs", "Банкомати"),
        # Інтернет-послуги
        (5815, "digital", "wants", "Цифрові товари"),
        (5816, "digital", "wants", "Цифрові ігри"),
        (5818, "digital", "wants", "Цифрові товари (інше)"),
    ]

    op.bulk_insert(
        mcc_category,
        [
            {
                "id": uuid.uuid4(),
                "mcc_code": mcc,
                "category_name": name,
                "category_group": group,
                "display_name_uk": display,
                "created_at": now,
                "updated_at": now,
            }
            for mcc, name, group, display in categories
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM mcc_category")
