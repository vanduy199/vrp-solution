from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.metrics_service import get_dashboard_metrics, get_route_metrics

router = APIRouter(prefix="/metrics")


@router.get("/dashboard")
def dashboard_metrics(db: Session = Depends(get_db)):
    return get_dashboard_metrics(db)


@router.get("/routes/{route_id}")
def route_metrics(route_id: str, db: Session = Depends(get_db)):
    return get_route_metrics(db, route_id)
