from __future__ import annotations

from datetime import datetime, timezone
from typing import cast

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.enums import RouteStatus, StopStatus, TrackingStatus
from app.core.ids import generate_id
from app.models.active_route import ActiveRoute
from app.models.route import Route
from app.models.route_stop import RouteStop
from app.repositories.route_repo import RouteRepository
from app.repositories.route_stop_repo import RouteStopRepository
from app.schemas.route import RouteAdjust, RouteStatusUpdate


def get_route_or_404(db: Session, route_id: str) -> Route:
    route = RouteRepository(db).get(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route


def list_routes(db: Session) -> list[Route]:
    return RouteRepository(db).list()


def list_active_routes(db: Session) -> list[Route]:
    return RouteRepository(db).list_active()


def delete_route(db: Session, route_id: str) -> None:
    route = get_route_or_404(db, route_id)
    if route.status in {RouteStatus.DISPATCHED.value, RouteStatus.IN_PROGRESS.value}:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a route that is dispatched or in progress",
        )
    RouteRepository(db).delete(route)


def dispatch_route(db: Session, route_id: str) -> Route:
    route = get_route_or_404(db, route_id)
    if route.status not in {RouteStatus.PLANNED.value}:
        raise HTTPException(
            status_code=409,
            detail=f"Route cannot be dispatched from status '{route.status}'",
        )

    now = datetime.now(timezone.utc)
    first_stop = route.stops[0] if route.stops else None

    active = db.get(ActiveRoute, route_id)
    if active is None:
        active = ActiveRoute(route_id=route_id)
        db.add(active)

    active.progress_percentage = 0.0
    active.current_lat = float(route.depot.lat if route.depot else 0.0)
    active.current_lng = float(route.depot.lng if route.depot else 0.0)
    active.next_stop_id = cast(str | None, first_stop.id if first_stop else None)
    active.current_stop_id = None
    active.delay_mins = 0
    active.tracking_status = TrackingStatus.ON_TIME.value
    active.updated_at = now

    route.status = RouteStatus.DISPATCHED.value
    route.dispatched_at = now
    route.updated_at = now
    db.commit()
    db.refresh(route)
    return route


def complete_route(db: Session, route_id: str) -> Route:
    route = get_route_or_404(db, route_id)
    now = datetime.now(timezone.utc)

    active = db.get(ActiveRoute, route_id)
    if active:
        db.delete(active)

    db.query(RouteStop).filter(
        RouteStop.route_id == route_id,
        RouteStop.status == StopStatus.PENDING.value,
    ).update({"status": StopStatus.COMPLETED.value})

    route.status = RouteStatus.COMPLETED.value
    route.completed_at = now
    route.updated_at = now
    db.commit()
    db.refresh(route)
    return route


def update_route_status(db: Session, route_id: str, payload: RouteStatusUpdate) -> Route:
    route = get_route_or_404(db, route_id)
    updates: dict = {"status": payload.status.value, "updated_at": datetime.now(timezone.utc)}
    if payload.note is not None:
        updates["status_note"] = payload.note
    if payload.status == RouteStatus.COMPLETED:
        updates["completed_at"] = datetime.now(timezone.utc)
        active = db.get(ActiveRoute, route_id)
        if active:
            db.delete(active)
    return RouteRepository(db).update(route, **updates)


def adjust_route(db: Session, route_id: str, payload: RouteAdjust) -> dict:
    source = get_route_or_404(db, payload.source_route_id)
    target = get_route_or_404(db, payload.target_route_id)

    stop_repo = RouteStopRepository(db)
    stop = db.query(RouteStop).filter(
        RouteStop.route_id == payload.source_route_id,
        RouteStop.id == payload.stop_id,
    ).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found in source route")

    old_seq = stop.sequence_index

    db.query(RouteStop).filter(
        RouteStop.route_id == payload.source_route_id,
        RouteStop.sequence_index > old_seq,
    ).update({"sequence_index": RouteStop.sequence_index - 1})

    db.query(RouteStop).filter(
        RouteStop.route_id == payload.target_route_id,
        RouteStop.sequence_index >= payload.new_sequence_index,
    ).update({"sequence_index": RouteStop.sequence_index + 1})

    stop.route_id = payload.target_route_id
    stop.sequence_index = payload.new_sequence_index
    db.commit()

    return {
        "stop_id": payload.stop_id,
        "source_route_id": payload.source_route_id,
        "target_route_id": payload.target_route_id,
        "new_sequence_index": payload.new_sequence_index,
        "locked": True,
    }
