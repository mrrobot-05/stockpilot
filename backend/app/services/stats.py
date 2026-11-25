from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Category, Product, StockMovement, Supplier
from app.schemas import MovementRead, StatsRead

RECENT_LIMIT = 10


def _int(db: Session, stmt) -> int:
    return int(db.scalar(stmt) or 0)


def _float(db: Session, stmt) -> float:
    return float(db.scalar(stmt) or 0)


def get_stats(db: Session) -> StatsRead:
    """Aggregate dashboard figures with a small number of grouped queries."""
    recent = db.scalars(
        select(StockMovement)
        .options(selectinload(StockMovement.product))
        .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
        .limit(RECENT_LIMIT)
    ).all()

    return StatsRead(
        total_products=_int(db, select(func.count()).select_from(Product)),
        active_products=_int(
            db,
            select(func.count())
            .select_from(Product)
            .where(Product.is_active.is_(True)),
        ),
        total_stock_units=_int(
            db, select(func.coalesce(func.sum(Product.quantity), 0))
        ),
        stock_cost_value=_float(
            db,
            select(func.coalesce(func.sum(Product.quantity * Product.cost_price), 0)),
        ),
        stock_retail_value=_float(
            db,
            select(func.coalesce(func.sum(Product.quantity * Product.sell_price), 0)),
        ),
        low_stock_count=_int(
            db,
            select(func.count())
            .select_from(Product)
            .where(Product.quantity > 0, Product.quantity <= Product.reorder_level),
        ),
        out_of_stock_count=_int(
            db,
            select(func.count())
            .select_from(Product)
            .where(Product.quantity == 0),
        ),
        category_count=_int(db, select(func.count()).select_from(Category)),
        supplier_count=_int(db, select(func.count()).select_from(Supplier)),
        recent_movements=[MovementRead.model_validate(item) for item in recent],
    )
