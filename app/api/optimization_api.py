from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.repositories import get_points
from app.services.optimization_service import optimize_route, optimize_ga

router = APIRouter()


@router.post("/optimize/nearest-neighbor")
def optimize(db: Session = Depends(get_db)):

    points = get_points(db)

    result = optimize_route(points)

    return {
        "success": True,
        "data": result
    }
@router.post("/optimize/genetic-algorithm")
def optimize_ga_route(db: Session = Depends(get_db)):

    points = get_points(db)

    result = optimize_ga(points)

    return {
        "success": True,
        "data": result
    }