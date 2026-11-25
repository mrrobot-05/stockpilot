from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Product
from app.schemas import ProductCreate, ProductUpdate

SORT_FIELDS = frozenset({"id", "sku", "name", "quantity", "sell_price", "created_at"})
DEFAULT_SORT = "id"
DEFAULT_PAGE_SIZE = 20


def _sort_column(sort: str):
    """Return an ordered column expression for an allowlisted sort key."""
    descending = sort.startswith("-")
    field = sort[1:] if descending else sort
    if field not in SORT_FIELDS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid sort field: {sort}",
        )
    column = getattr(Product, field)
    return column.desc() if descending else column.asc()


def _ensure_unique_sku(db: Session, sku: str, exclude_id: int | None = None) -> None:
    """Reject a SKU already used by another product (case-insensitive)."""
    stmt = select(Product.id).where(func.lower(Product.sku) == sku.lower())
    if exclude_id is not None:
        stmt = stmt.where(Product.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this SKU already exists",
        )


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards so user-supplied searches match literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_products(
    db: Session,
    q: str | None = None,
    low_stock: bool = False,
    sort: str = DEFAULT_SORT,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[Product], int]:
    """Return one page of products and the total number of matching rows."""
    stmt = select(Product)
    if q:
        pattern = f"%{_escape_like(q)}%"
        stmt = stmt.where(
            or_(
                Product.sku.ilike(pattern, escape="\\"),
                Product.name.ilike(pattern, escape="\\"),
                Product.description.ilike(pattern, escape="\\"),
            )
        )
    if low_stock:
        stmt = stmt.where(Product.quantity <= Product.reorder_level)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = (
        stmt.order_by(_sort_column(sort), Product.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(stmt).all()), total


def create_product(db: Session, payload: ProductCreate) -> Product:
    _ensure_unique_sku(db, payload.sku)
    product = Product(**payload.model_dump())
    db.add(product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A product with this SKU already exists"
        )
    db.refresh(product)
    return product


def get_product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return product


def update_product(db: Session, product_id: int, payload: ProductUpdate) -> Product:
    product = get_product(db, product_id)
    changes = payload.model_dump(exclude_unset=True)
    if "sku" in changes:
        _ensure_unique_sku(db, changes["sku"], exclude_id=product_id)
    for field, value in changes.items():
        setattr(product, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A product with this SKU already exists"
        )
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int) -> None:
    product = get_product(db, product_id)
    db.delete(product)
    db.commit()
