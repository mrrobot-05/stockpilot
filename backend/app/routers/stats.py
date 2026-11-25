from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import StatsRead
from app.services import stats as stats_service

router = APIRouter(tags=["stats"])


@router.get("/api/stats", response_model=StatsRead)
def get_stats(db: Session = Depends(get_db)) -> StatsRead:
    return stats_service.get_stats(db)
