import math

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import MovementType, StockMovement
from app.schemas import MovementCreate, MovementPage, MovementRead
from app.services import movements as movement_service

router = APIRouter(tags=["movements"])


def _page(
    items: list[StockMovement], total: int, page: int, page_size: int
) -> MovementPage:
    return MovementPage(
        items=[MovementRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.post(
    "/api/products/{product_id}/movements",
    response_model=MovementRead,
    status_code=status.HTTP_201_CREATED,
)
def create_movement(
    product_id: int, payload: MovementCreate, db: Session = Depends(get_db)
) -> MovementRead:
    return MovementRead.model_validate(
        movement_service.create_movement(db, product_id, payload)
    )


@router.get("/api/products/{product_id}/movements", response_model=MovementPage)
def list_product_movements(
    product_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort: str = "-created_at",
    db: Session = Depends(get_db),
) -> MovementPage:
    items, total = movement_service.list_product_movements(
        db, product_id, page=page, page_size=page_size, sort=sort
    )
    return _page(items, total, page, page_size)


@router.get("/api/movements", response_model=MovementPage)
def list_movements(
    product_id: int | None = None,
    movement_type: MovementType | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort: str = "-created_at",
    db: Session = Depends(get_db),
) -> MovementPage:
    items, total = movement_service.list_movements(
        db,
        product_id=product_id,
        movement_type=movement_type,
        page=page,
        page_size=page_size,
        sort=sort,
    )
    return _page(items, total, page, page_size)
