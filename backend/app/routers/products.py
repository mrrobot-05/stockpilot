import math

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import ProductCreate, ProductPage, ProductRead, ProductUpdate
from app.services import products as product_service

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=ProductPage)
def list_products(
    q: str | None = None,
    low_stock: bool = False,
    sort: str = "id",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category_id: int | None = None,
    supplier_id: int | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
) -> ProductPage:
    items, total = product_service.list_products(
        db,
        q=q,
        low_stock=low_stock,
        sort=sort,
        page=page,
        page_size=page_size,
        category_id=category_id,
        supplier_id=supplier_id,
        is_active=is_active,
    )
    return ProductPage(
        items=[ProductRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> ProductRead:
    product = product_service.create_product(db, payload)
    return ProductRead.model_validate(product)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductRead:
    return ProductRead.model_validate(product_service.get_product(db, product_id))


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)
) -> ProductRead:
    product = product_service.update_product(db, product_id, payload)
    return ProductRead.model_validate(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)) -> None:
    product_service.delete_product(db, product_id)
