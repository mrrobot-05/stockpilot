from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import CategoryCreate, CategoryRead, CategoryUpdate
from app.services import categories as category_service

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
def list_categories(
    q: str | None = None, db: Session = Depends(get_db)
) -> list[CategoryRead]:
    rows = category_service.list_categories(db, q=q)
    return [
        CategoryRead.model_validate(category).model_copy(update={"product_count": count})
        for category, count in rows
    ]


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate, db: Session = Depends(get_db)
) -> CategoryRead:
    return CategoryRead.model_validate(category_service.create_category(db, payload))


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id: int, db: Session = Depends(get_db)) -> CategoryRead:
    return CategoryRead.model_validate(category_service.get_category(db, category_id))


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)
) -> CategoryRead:
    category = category_service.update_category(db, category_id, payload)
    return CategoryRead.model_validate(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)) -> None:
    category_service.delete_category(db, category_id)
