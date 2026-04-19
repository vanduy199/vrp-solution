from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.kafka_service import publish_test_event
from app.services.optimization_service import optimize_route, optimize_ga
from app.services.point_service import list_points as service_list_points

router = APIRouter()


@router.post("/optimize/nearest-neighbor")
def optimize_nearest_neighbor(db: Session = Depends(get_db)):
    points = service_list_points(db)
    result = optimize_route(points)
    return {
        "success": True,
        "data": result,
    }


@router.post("/optimize/genetic-algorithm")
def optimize_genetic_algorithm(db: Session = Depends(get_db)):
    points = service_list_points(db)
    result = optimize_ga(points)
    return {
        "success": True,
        "data": result,
    }

@router.get("/test")
def test(background_tasks: BackgroundTasks):
    event_id = str(uuid4())
    event_payload = {
        "event_id": event_id,
        "event_type": "API_TEST_CALLED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "path": "/api/test",
    }
    background_tasks.add_task(publish_test_event, event_payload)

    return {
        "success": True,
        "message": "API is working! Event queued to Kafka in background.",
        "data": {
            "event_id": event_id,
        },
    }
