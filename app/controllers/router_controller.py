from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.point_service import list_points,  
from app.models.point import Point

router = APIRouter()


@router.get("/")
def root():
    return {"message": "VRP Optimization API is running"}


@router.get("/points")
def get_points(db: Session = Depends(get_db)):
    points = list_points(db)
    return {
        "count": len(points),
        "data": points,
    }


@router.post("/points")
def create_point(db: Session = Depends(get_db),p: Point):
    

