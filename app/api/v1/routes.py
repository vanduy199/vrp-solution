from __future__ import annotations

import io
from typing import cast

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import RouteStatus, StopStatus
from app.schemas.common import SuccessResponse
from app.schemas.route import (
    ActiveRouteResponse,
    RouteAdjust,
    RouteDetail,
    RouteStatus as RouteStatusEnum,
    RouteStatusUpdate,
    RouteSummary,
    RouteStopResponse,
)
from app.services.route_service import (
    adjust_route,
    complete_route,
    delete_route,
    dispatch_route,
    get_route_or_404,
    list_active_routes,
    list_routes,
    update_route_status,
)
from app.services.optimization_service import materialize_job
from app.models.optimization_job import OptimizationJob

router = APIRouter(prefix="/routes")


def _route_summary(route) -> RouteSummary:
    return RouteSummary(
        id=route.id,
        vehicle_id=route.vehicle_id,
        depot_id=route.depot_id,
        job_id=route.job_id,
        status=RouteStatus(route.status),
        total_distance_km=route.total_distance_km,
        total_duration_mins=route.total_duration_mins,
        total_cost=route.total_cost,
        load_kg=route.load_kg,
        utilization_pct=route.utilization_pct,
        stop_count=len(route.stops),
    )


def _route_detail(route) -> RouteDetail:
    return RouteDetail(
        id=route.id,
        vehicle_id=route.vehicle_id,
        depot_id=route.depot_id,
        job_id=route.job_id,
        status=RouteStatus(route.status),
        status_note=route.status_note,
        total_distance_km=route.total_distance_km,
        total_duration_mins=route.total_duration_mins,
        total_cost=route.total_cost,
        load_kg=route.load_kg,
        utilization_pct=route.utilization_pct,
        stop_count=len(route.stops),
        stops=[RouteStopResponse.from_model(s) for s in route.stops],
        created_at=route.created_at,
        updated_at=route.updated_at,
        dispatched_at=route.dispatched_at,
        completed_at=route.completed_at,
    )


@router.get("", response_model=list[RouteSummary])
def get_routes(db: Session = Depends(get_db)):
    for job in db.query(OptimizationJob).all():
        materialize_job(db, job)
    return [_route_summary(r) for r in list_routes(db)]


@router.get("/active", response_model=list[ActiveRouteResponse])
def get_active_routes(db: Session = Depends(get_db)):
    result = []
    for route in list_active_routes(db):
        ar = route.active
        if not ar:
            continue
        driver_name = None
        if route.vehicle and route.vehicle.driver:
            driver_name = route.vehicle.driver.full_name

        next_stop = None
        if ar.next_stop_id:
            ns = ar.next_stop
            if ns:
                next_stop = RouteStopResponse.from_model(ns)

        from app.core.enums import TrackingStatus
        from app.schemas.common import Coordinates
        result.append(
            ActiveRouteResponse(
                route_id=route.id,
                vehicle_id=route.vehicle_id,
                driver_name=driver_name,
                tracking_status=TrackingStatus(ar.tracking_status),
                progress_percentage=ar.progress_percentage,
                current_coordinates=Coordinates(lat=ar.current_lat, lng=ar.current_lng),
                next_stop=next_stop,
                delay_mins=ar.delay_mins,
                updated_at=ar.updated_at,
            )
        )
    return result


@router.get("/{route_id}", response_model=RouteDetail)
def get_route(route_id: str, db: Session = Depends(get_db)):
    return _route_detail(get_route_or_404(db, route_id))


@router.get("/{route_id}/manifest")
def get_route_manifest(route_id: str, db: Session = Depends(get_db)):
    route = get_route_or_404(db, route_id)
    driver_name = None
    if route.vehicle and route.vehicle.driver:
        driver_name = route.vehicle.driver.full_name
    stops = [
        {
            "stop_id": s.id,
            "location_id": s.location_id,
            "name": s.location.name if s.location else "Unknown",
            "address": s.location.address if s.location else "",
            "sequence": s.sequence_index,
            "status": s.status,
        }
        for s in route.stops
    ]
    return {
        "route_id": route.id,
        "vehicle_id": route.vehicle_id,
        "driver_name": driver_name,
        "status": route.status,
        "stops": stops,
    }


@router.post("/{route_id}/dispatch")
def dispatch_route_endpoint(route_id: str, db: Session = Depends(get_db)):
    route = dispatch_route(db, route_id)
    return {"success": True, "route_id": route.id, "status": route.status}


@router.post("/{route_id}/complete")
def complete_route_endpoint(route_id: str, db: Session = Depends(get_db)):
    route = complete_route(db, route_id)
    return {"success": True, "route_id": route.id, "status": route.status}


@router.post("/{route_id}/status")
def update_status_endpoint(route_id: str, payload: RouteStatusUpdate, db: Session = Depends(get_db)):
    route = update_route_status(db, route_id, payload)
    return {"success": True, "route_id": route.id, "status": route.status}


@router.post("/{route_id}/adjust")
def adjust_route_endpoint(route_id: str, payload: RouteAdjust, db: Session = Depends(get_db)):
    result = adjust_route(db, route_id, payload)
    return {"success": True, "data": result}


@router.delete("/{route_id}", status_code=204)
def delete_route_endpoint(route_id: str, db: Session = Depends(get_db)):
    delete_route(db, route_id)


@router.get("/{route_id}/export")
def export_route(
    route_id: str,
    format: str = Query("json", pattern="^(json|xlsx|pdf)$"),
    db: Session = Depends(get_db),
):
    route = get_route_or_404(db, route_id)
    driver_name = route.vehicle.driver.full_name if route.vehicle and route.vehicle.driver else "Unknown"

    if format == "json":
        return _route_detail(route)

    if format == "xlsx":
        lines = [
            "route_id\tvehicle_id\tstatus\ttotal_distance_km\ttotal_duration_mins\tstop_count",
            f"{route.id}\t{route.vehicle_id}\t{route.status}\t"
            f"{route.total_distance_km}\t{route.total_duration_mins}\t{len(route.stops)}",
        ]
        data = "\n".join(lines).encode("utf-8")
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=route-{route_id}.xlsx"},
        )

    pdf_text = (
        f"Route Report\n"
        f"Route ID: {route.id}\n"
        f"Vehicle: {route.vehicle_id}\n"
        f"Driver: {driver_name}\n"
        f"Status: {route.status}\n"
        f"Distance: {route.total_distance_km} km\n"
        f"Duration: {route.total_duration_mins} mins\n"
    )
    return StreamingResponse(
        io.BytesIO(pdf_text.encode("utf-8")),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=route-{route_id}.pdf"},
    )
