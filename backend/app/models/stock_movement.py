from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.product import Product


class MovementType(str, enum.Enum):
    IN = "IN"
    OUT = "OUT"
    ADJUST = "ADJUST"


class StockMovement(Base):
    """An immutable ledger row; stock changes are recorded here, never edited."""

    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    movement_type: Mapped[MovementType] = mapped_column(
        Enum(
            MovementType,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_after: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )

    product: Mapped[Product] = relationship(back_populates="movements")

    def __repr__(self) -> str:
        return (
            f"<StockMovement id={self.id} product_id={self.product_id} "
            f"type={self.movement_type.value} change={self.quantity_change}>"
        )
