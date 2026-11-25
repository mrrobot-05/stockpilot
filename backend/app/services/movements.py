from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import MovementType, Product, StockMovement
from app.schemas import MovementCreate

SORT_FIELDS = frozenset({"id", "created_at", "quantity", "movement_type", "stock_after"})
DEFAULT_SORT = "-created_at"
DEFAULT_PAGE_SIZE = 20


def _sort_column(sort: str):
    """Return an ordered column expression for an allowlisted sort key."""
    descending = sort.startswith("-")
    field = sort[1:] if descending else sort
    if field not in SORT_FIELDS:
        raise HTTPException(
            status_code=422, detail=f"Invalid sort field: {sort}"
        )
    column = getattr(StockMovement, field)
    return column.desc() if descending else column.asc()


def create_movement(
    db: Session, product_id: int, payload: MovementCreate
) -> StockMovement:
    """Record a movement and apply its delta to stock in one transaction."""
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    old_stock = product.quantity
    if payload.movement_type == MovementType.IN:
        new_stock = old_stock + payload.quantity
        delta = payload.quantity
    elif payload.movement_type == MovementType.OUT:
        new_stock = old_stock - payload.quantity
        if new_stock < 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Insufficient stock"
            )
        delta = -payload.quantity
    else:  # ADJUST: quantity is the new absolute stock level
        new_stock = payload.quantity
        delta = new_stock - old_stock

    movement = StockMovement(
        product_id=product_id,
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        quantity_change=delta,
        stock_after=new_stock,
        note=payload.note,
    )
    db.add(movement)
    product.quantity = new_stock
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stock movement could not be recorded",
        )

    # Re-fetch with the product eagerly loaded for a stable read model.
    return db.scalars(
        select(StockMovement)
        .where(StockMovement.id == movement.id)
        .options(selectinload(StockMovement.product))
    ).one()


def list_movements(
    db: Session,
    product_id: int | None = None,
    movement_type: MovementType | None = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    sort: str = DEFAULT_SORT,
) -> tuple[list[StockMovement], int]:
    """Return one page of movements and the total number of matching rows."""
    stmt = select(StockMovement).options(selectinload(StockMovement.product))
    if product_id is not None:
        stmt = stmt.where(StockMovement.product_id == product_id)
    if movement_type is not None:
        stmt = stmt.where(StockMovement.movement_type == movement_type)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(_sort_column(sort), StockMovement.id.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    return list(db.scalars(stmt).all()), total


def list_product_movements(
    db: Session,
    product_id: int,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    sort: str = DEFAULT_SORT,
) -> tuple[list[StockMovement], int]:
    """List movements for one product, 404 if the product does not exist."""
    if db.get(Product, product_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return list_movements(
        db, product_id=product_id, page=page, page_size=page_size, sort=sort
    )
