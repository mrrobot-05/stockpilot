from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import exports as exports_service

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/products.csv")
def export_products(db: Session = Depends(get_db)) -> Response:
    return Response(
        content=exports_service.products_csv(db),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="products.csv"'},
    )


@router.get("/movements.csv")
def export_movements(db: Session = Depends(get_db)) -> Response:
    return Response(
        content=exports_service.movements_csv(db),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="movements.csv"'},
    )
