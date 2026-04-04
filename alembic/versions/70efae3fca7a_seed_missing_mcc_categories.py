"""seed missing mcc categories

Revision ID: 70efae3fca7a
Revises: ca817299bac8
Create Date: 2026-04-05 00:05:47.901354

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70efae3fca7a'
down_revision: Union[str, None] = 'ca817299bac8'
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
        # Транспорт / Доставка
        (4112, "transport", "needs", "Залізничний транспорт"),
        (4214, "transport", "needs", "Вантажні перевезення"),
        (4215, "delivery", "needs", "Кур'єрська доставка"),
        # Подорожі
        (4722, "travel", "wants", "Туристичні агентства"),
        # Фінансові послуги
        (4829, "financial", "needs", "Грошові перекази"),
        # Дім / Будівництво
        (5200, "home", "needs", "Будматеріали"),
        (5211, "home", "needs", "Будівельні магазини"),
        # Продукти
        (5499, "groceries", "needs", "Продуктові магазини (інше)"),
        # Одяг
        (5691, "clothing", "wants", "Магазини одягу"),
        (5699, "clothing", "wants", "Аксесуари / Одяг (інше)"),
        # Побутова техніка
        (5722, "electronics", "wants", "Побутова техніка"),
        # Кейтеринг
        (5811, "restaurants", "wants", "Кейтеринг"),
        # Алкоголь
        (5921, "alcohol", "wants", "Алкоголь"),
        # Покупки
        (5399, "shopping", "wants", "Інші товари"),
        (5943, "shopping", "wants", "Канцтовари"),
        (5947, "shopping", "wants", "Подарунки / Сувеніри"),
        (5999, "shopping", "wants", "Інші магазини"),
        # Краса
        (5977, "beauty", "wants", "Косметика / Парфумерія"),
        # Послуги
        (7277, "services", "needs", "Консалтинг"),
        (8999, "services", "needs", "Професійні послуги"),
        # Розваги
        (7991, "entertainment", "wants", "Туристичні атракціони"),
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
    op.execute(
        "DELETE FROM mcc_category WHERE mcc_code IN "
        "(4112,4214,4215,4722,4829,5200,5211,5499,5691,5699,"
        "5722,5811,5921,5399,5943,5947,5999,5977,7277,8999,7991)"
    )
