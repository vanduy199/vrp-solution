from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dto.point_dto import PointCreateDTO, PointUpdateDTO
from app.services.point_service import create_point, list_points, update_point, delete_point

router = APIRouter()


@router.get("/")
def root():
    return {"message": "VRP Optimization API is running"}


@router.get("/points")
def get_points(db: Session = Depends(get_db)):
    points = list_points(db)

    data = [
        {
            "id": p.id,
            "name": p.name,
            "latitude": p.latitude,
            "longitude": p.longitude,
            "demand": p.demand,
            "priority": p.priority,
            "phone": p.phone,
            "time_window_start": p.time_window_start,
            "time_window_end": p.time_window_end,
            "service_time": p.service_time,
            "address": p.address,
        }
        for p in points
    ]

    return {
        "count": len(data),
        "data": data,
    }


@router.post("/points")
def create_point_api(payload: PointCreateDTO, db: Session = Depends(get_db)):
    point = create_point(db, payload.model_dump())
    return {
        "success": True,
        "data": {
            "id": point.id,
            "name": point.name,
            "latitude": point.latitude,
            "longitude": point.longitude,
            "demand": point.demand,
            "priority": point.priority,
            "phone": point.phone,
            "time_window_start": point.time_window_start,
            "time_window_end": point.time_window_end,
            "service_time": point.service_time,
            "address": point.address,
        },
    }

@router.put("/points/{point_id}")
def update_point_api(point_id: str, payload: PointUpdateDTO, db: Session = Depends(get_db)):
    point = update_point(db, point_id, payload.model_dump(exclude_unset=True))
    if not point:
        return {
            "success": False,
            "message": "Point not found",
        }
    return {
        "success": True,
        "data": {
            "id": point.id, 
            "name": point.name,
            "latitude": point.latitude,
            "longitude": point.longitude,
            "demand": point.demand,
            "priority": point.priority,
            "phone": point.phone,
            "time_window_start": point.time_window_start,
            "time_window_end": point.time_window_end,
            "service_time": point.service_time,
            "address": point.address,
        },
    }


@router.delete("/points/{point_id}")
def delete_point_api(point_id: str, db: Session = Depends(get_db)):
    point = delete_point(db, point_id)
    if not point:
        return {
            "success": False,
            "message": "Point not found",
        }
    return {
        "success": True,
        "message": "Point deleted successfully",
    }