from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Category, Product
from app.schemas import CategoryCreate, CategoryUpdate


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards so user-supplied searches match literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _ensure_unique_name(db: Session, name: str, exclude_id: int | None = None) -> None:
    """Reject a category name already used by another row (case-insensitive)."""
    stmt = select(Category.id).where(func.lower(Category.name) == name.lower())
    if exclude_id is not None:
        stmt = stmt.where(Category.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this name already exists",
        )


def list_categories(db: Session, q: str | None = None) -> list[tuple[Category, int]]:
    """Return every matching category with its product count in one grouped query."""
    stmt = (
        select(Category, func.count(Product.id).label("product_count"))
        .outerjoin(Product, Product.category_id == Category.id)
        .group_by(Category.id, Category.name)
        .order_by(Category.name.asc())
    )
    if q:
        pattern = f"%{_escape_like(q)}%"
        stmt = stmt.where(
            or_(
                Category.name.ilike(pattern, escape="\\"),
                Category.description.ilike(pattern, escape="\\"),
            )
        )
    return [(row[0], row[1]) for row in db.execute(stmt).all()]


def get_category(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    return category


def create_category(db: Session, payload: CategoryCreate) -> Category:
    name = payload.name.strip()
    _ensure_unique_name(db, name)
    category = Category(name=name, description=payload.description)
    db.add(category)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A category with this name already exists"
        )
    db.refresh(category)
    return category


def update_category(db: Session, category_id: int, payload: CategoryUpdate) -> Category:
    category = get_category(db, category_id)
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes:
        changes["name"] = changes["name"].strip()
        _ensure_unique_name(db, changes["name"], exclude_id=category_id)
    for field, value in changes.items():
        setattr(category, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A category with this name already exists"
        )
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int) -> None:
    category = get_category(db, category_id)
    db.execute(
        update(Product)
        .where(Product.category_id == category_id)
        .values(category_id=None)
    )
    db.delete(category)
    db.commit()
