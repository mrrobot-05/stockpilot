from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import SupplierCreate, SupplierRead, SupplierUpdate
from app.services import suppliers as supplier_service

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


@router.get("", response_model=list[SupplierRead])
def list_suppliers(
    q: str | None = None, db: Session = Depends(get_db)
) -> list[SupplierRead]:
    rows = supplier_service.list_suppliers(db, q=q)
    return [
        SupplierRead.model_validate(supplier).model_copy(update={"product_count": count})
        for supplier, count in rows
    ]


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate, db: Session = Depends(get_db)
) -> SupplierRead:
    return SupplierRead.model_validate(supplier_service.create_supplier(db, payload))


@router.get("/{supplier_id}", response_model=SupplierRead)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)) -> SupplierRead:
    return SupplierRead.model_validate(supplier_service.get_supplier(db, supplier_id))


@router.patch("/{supplier_id}", response_model=SupplierRead)
def update_supplier(
    supplier_id: int, payload: SupplierUpdate, db: Session = Depends(get_db)
) -> SupplierRead:
    supplier = supplier_service.update_supplier(db, supplier_id, payload)
    return SupplierRead.model_validate(supplier)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)) -> None:
    supplier_service.delete_supplier(db, supplier_id)
