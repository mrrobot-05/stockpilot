"""add case-insensitive unique indexes

Revision ID: b2c3d4e5f6a7
Revises: f1a2b3c4d5e6
Create Date: 2026-11-26 05:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_products_sku_lower", "products", [sa.text("lower(sku)")], unique=True
    )
    op.create_index(
        "uq_categories_name_lower",
        "categories",
        [sa.text("lower(name)")],
        unique=True,
    )
    op.create_index(
        "uq_suppliers_name_lower",
        "suppliers",
        [sa.text("lower(name)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_suppliers_name_lower", table_name="suppliers")
    op.drop_index("uq_categories_name_lower", table_name="categories")
    op.drop_index("uq_products_sku_lower", table_name="products")
