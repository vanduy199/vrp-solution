from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.enums import RouteStatus, StopStatus
from app.models.active_route import ActiveRoute
from app.models.route import Route
from app.models.route_stop import RouteStop
from app.schemas.driver import DriverStopStatusUpdate


def get_driver_manifest(db: Session) -> list[dict]:
    active_routes = (
        db.query(Route)
        .join(ActiveRoute, ActiveRoute.route_id == Route.id)
        .all()
    )
    result = []
    for route in active_routes:
        driver_name = None
        if route.vehicle and route.vehicle.driver:
            driver_name = route.vehicle.driver.full_name
        result.append(
            {
                "route_id": route.id,
                "vehicle_id": route.vehicle_id,
                "driver_name": driver_name,
                "stops": route.stops,
            }
        )
    return result


def get_stop_or_404(db: Session, stop_id: str) -> RouteStop:
    stop = db.get(RouteStop, stop_id)
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")
    return stop


def update_stop_status(db: Session, stop_id: str, payload: DriverStopStatusUpdate) -> RouteStop:
    stop = get_stop_or_404(db, stop_id)
    now = datetime.now(timezone.utc)

    stop.status = payload.status.value
    if payload.proof_of_delivery_url is not None:
        stop.proof_of_delivery_url = payload.proof_of_delivery_url
    if payload.notes is not None:
        stop.notes = payload.notes
    if payload.status == StopStatus.COMPLETED:
        stop.actual_completed_at = now
    elif payload.status == StopStatus.ARRIVED:
        stop.actual_arrived_at = now
    stop.updated_at = now

    _sync_route_progress(db, stop.route_id)
    db.commit()
    db.refresh(stop)
    return stop


def _sync_route_progress(db: Session, route_id: str) -> None:
    route = db.get(Route, route_id)
    if not route:
        return

    stops = route.stops
    total = len(stops)
    if total == 0:
        return

    completed = sum(
        1 for s in stops
        if s.status in {StopStatus.COMPLETED.value, StopStatus.SKIPPED.value, StopStatus.FAILED.value}
    )

    active = db.get(ActiveRoute, route_id)
    if active:
        active.progress_percentage = round((completed / total) * 100, 2)

        pending_stops = [s for s in stops if s.status == StopStatus.PENDING.value]
        active.next_stop_id = pending_stops[0].id if pending_stops else None

        current_stops = [s for s in stops if s.status == StopStatus.ARRIVED.value]
        active.current_stop_id = current_stops[0].id if current_stops else None
        active.updated_at = datetime.now(timezone.utc)

    if completed == total and route.status != RouteStatus.COMPLETED.value:
        route.status = RouteStatus.COMPLETED.value
        route.completed_at = datetime.now(timezone.utc)
        if active:
            db.delete(active)
