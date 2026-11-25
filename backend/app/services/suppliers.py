from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Product, Supplier
from app.schemas import SupplierCreate, SupplierUpdate


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards so user-supplied searches match literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _ensure_unique_name(db: Session, name: str, exclude_id: int | None = None) -> None:
    """Reject a supplier name already used by another row (case-insensitive)."""
    stmt = select(Supplier.id).where(func.lower(Supplier.name) == name.lower())
    if exclude_id is not None:
        stmt = stmt.where(Supplier.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A supplier with this name already exists",
        )


def list_suppliers(db: Session, q: str | None = None) -> list[tuple[Supplier, int]]:
    """Return every matching supplier with its product count in one grouped query."""
    stmt = (
        select(Supplier, func.count(Product.id).label("product_count"))
        .outerjoin(Product, Product.supplier_id == Supplier.id)
        .group_by(Supplier.id, Supplier.name)
        .order_by(Supplier.name.asc())
    )
    if q:
        pattern = f"%{_escape_like(q)}%"
        stmt = stmt.where(
            or_(
                Supplier.name.ilike(pattern, escape="\\"),
                Supplier.contact_name.ilike(pattern, escape="\\"),
                Supplier.email.ilike(pattern, escape="\\"),
                Supplier.phone.ilike(pattern, escape="\\"),
                Supplier.address.ilike(pattern, escape="\\"),
                Supplier.notes.ilike(pattern, escape="\\"),
            )
        )
    return [(row[0], row[1]) for row in db.execute(stmt).all()]


def get_supplier(db: Session, supplier_id: int) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found"
        )
    return supplier


def create_supplier(db: Session, payload: SupplierCreate) -> Supplier:
    name = payload.name.strip()
    _ensure_unique_name(db, name)
    supplier = Supplier(
        name=name,
        contact_name=payload.contact_name,
        email=payload.email,
        phone=payload.phone,
        address=payload.address,
        notes=payload.notes,
    )
    db.add(supplier)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A supplier with this name already exists"
        )
    db.refresh(supplier)
    return supplier


def update_supplier(
    db: Session, supplier_id: int, payload: SupplierUpdate
) -> Supplier:
    supplier = get_supplier(db, supplier_id)
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes:
        changes["name"] = changes["name"].strip()
        _ensure_unique_name(db, changes["name"], exclude_id=supplier_id)
    for field, value in changes.items():
        setattr(supplier, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A supplier with this name already exists"
        )
    db.refresh(supplier)
    return supplier


def delete_supplier(db: Session, supplier_id: int) -> None:
    supplier = get_supplier(db, supplier_id)
    db.execute(
        update(Product)
        .where(Product.supplier_id == supplier_id)
        .values(supplier_id=None)
    )
    db.delete(supplier)
    db.commit()
