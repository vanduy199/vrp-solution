from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.driver import DriverStopStatusUpdate
from app.schemas.route import RouteStopResponse
from app.services.driver_service import (
    get_driver_manifest,
    get_stop_or_404,
    update_stop_status,
)
from app.services.route_service import get_route_or_404

router = APIRouter(prefix="/driver")


@router.get("/manifest")
def get_manifest(db: Session = Depends(get_db)):
    manifests = get_driver_manifest(db)
    result = []
    for m in manifests:
        result.append(
            {
                "route_id": m["route_id"],
                "vehicle_id": m["vehicle_id"],
                "driver_name": m["driver_name"],
                "stops": [RouteStopResponse.from_model(s) for s in m["stops"]],
            }
        )
    return result


@router.get("/routes/{route_id}/stops")
def get_route_stops(route_id: str, db: Session = Depends(get_db)):
    route = get_route_or_404(db, route_id)
    return {
        "route_id": route_id,
        "stops": [RouteStopResponse.from_model(s) for s in route.stops],
    }


@router.get("/stops/{stop_id}", response_model=RouteStopResponse)
def get_stop(stop_id: str, db: Session = Depends(get_db)):
    return RouteStopResponse.from_model(get_stop_or_404(db, stop_id))


@router.put("/stops/{stop_id}/status", response_model=RouteStopResponse)
def update_stop(stop_id: str, payload: DriverStopStatusUpdate, db: Session = Depends(get_db)):
    stop = update_stop_status(db, stop_id, payload)
    return RouteStopResponse.from_model(stop)
