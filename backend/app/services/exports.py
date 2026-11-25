import csv
import io

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Product, StockMovement

PRODUCT_HEADER = [
    "sku",
    "name",
    "description",
    "category",
    "supplier",
    "cost_price",
    "sell_price",
    "quantity",
    "reorder_level",
    "is_active",
    "created_at",
    "updated_at",
]
MOVEMENT_HEADER = [
    "id",
    "created_at",
    "product_sku",
    "product_name",
    "movement_type",
    "quantity",
    "quantity_change",
    "stock_after",
    "note",
]

_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _safe_cell(value: object) -> object:
    """Neutralise spreadsheet formulas without changing numeric columns."""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def products_csv(db: Session) -> str:
    """Return all products as a deterministic CSV document."""
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(PRODUCT_HEADER)
    products = db.scalars(
        select(Product)
        .options(selectinload(Product.category), selectinload(Product.supplier))
        .order_by(Product.id)
    ).all()
    for product in products:
        writer.writerow(
            [
                _safe_cell(value)
                for value in [
                    product.sku,
                    product.name,
                    product.description or "",
                    product.category.name if product.category else "",
                    product.supplier.name if product.supplier else "",
                    f"{product.cost_price:.2f}",
                    f"{product.sell_price:.2f}",
                    product.quantity,
                    product.reorder_level,
                    "true" if product.is_active else "false",
                    product.created_at.isoformat(),
                    product.updated_at.isoformat(),
                ]
            ]
        )
    return output.getvalue()


def movements_csv(db: Session) -> str:
    """Return the movement ledger as a deterministic CSV document."""
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(MOVEMENT_HEADER)
    movements = db.scalars(
        select(StockMovement)
        .options(selectinload(StockMovement.product))
        .order_by(StockMovement.created_at, StockMovement.id)
    ).all()
    for movement in movements:
        writer.writerow(
            [
                _safe_cell(value)
                for value in [
                    movement.id,
                    movement.created_at.isoformat(),
                    movement.product.sku,
                    movement.product.name,
                    movement.movement_type.value,
                    movement.quantity,
                    movement.quantity_change,
                    movement.stock_after,
                    movement.note or "",
                ]
            ]
        )
    return output.getvalue()
