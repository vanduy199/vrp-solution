from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.optimization_service import optimize_route, optimize_ga
from app.services.point_service import list_points

router = APIRouter()


@router.post("/optimize/nearest-neighbor")
def optimize_nearest_neighbor(db: Session = Depends(get_db)):
    points = list_points(db)
    result = optimize_route(points)
    return {
        "success": True,
        "data": result,
    }


@router.post("/optimize/genetic-algorithm")
def optimize_genetic_algorithm(db: Session = Depends(get_db)):
    points = list_points(db)
    result = optimize_ga(points)
    return {
        "success": True,
        "data": result,
    }
