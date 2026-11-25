"""create stock movements ledger

Revision ID: f1a2b3c4d5e6
Revises: d4e7a9b1c2f3
Create Date: 2026-11-26 04:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "d4e7a9b1c2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column(
            "movement_type",
            sa.Enum(
                "IN",
                "OUT",
                "ADJUST",
                name="movement_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("quantity_change", sa.Integer(), nullable=False),
        sa.Column("stock_after", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_stock_movements_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_stock_movements_product_id"),
        "stock_movements",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_stock_movements_movement_type"),
        "stock_movements",
        ["movement_type"],
        unique=False,
    )
    op.create_index(
        "ix_stock_movements_created_at", "stock_movements", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_stock_movements_created_at", table_name="stock_movements")
    op.drop_index(
        op.f("ix_stock_movements_movement_type"), table_name="stock_movements"
    )
    op.drop_index(op.f("ix_stock_movements_product_id"), table_name="stock_movements")
    op.drop_table("stock_movements")
