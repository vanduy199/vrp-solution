from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.repositories import get_points

router = APIRouter()


# =============================
# Health check
# =============================
@router.get("/")
def root():
    return {
        "message": "VRP Optimization API is running"
    }


# =============================
# API test database
# =============================
@router.get("/points")
def list_points(db: Session = Depends(get_db)):
    points = get_points(db)

    return {
        "count": len(points),
        "data": points
    }