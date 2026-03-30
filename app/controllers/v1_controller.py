from __future__ import annotations

from datetime import datetime, timedelta, timezone
import io
from typing import Any, cast
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dto.v1_dto import (
    DepotCreateDTO,
    DepotUpdateDTO,
    DriverStopStatusUpdateDTO,
    LocationCreateDTO,
    LocationUpdateDTO,
    OptimizeRunRequestDTO,
    RouteAdjustDTO,
    RouteStatusUpdateDTO,
    UserCreateDTO,
    UserUpdateDTO,
    VehicleCreateDTO,
    VehicleUpdateDTO,
)
from app.models.point import Point
from app.models.route import Route
from app.models.vehicle import Vehicle
from app.models.route_detail import RouteDetail
from app.models.optimization_job import OptimizationJob
from app.models.active_route import ActiveRoute
from app.models.driver_stop import DriverStop

router = APIRouter(prefix="/v1")

# In-memory stores for entities not yet backed by DB models.
OPTIMIZATION_JOBS: dict[str, dict[str, Any]] = {}
ACTIVE_ROUTES: dict[str, dict[str, Any]] = {}
ROUTE_DETAILS: dict[str, dict[str, Any]] = {}
DEPOTS: dict[str, dict[str, Any]] = {}
USERS: dict[str, dict[str, Any]] = {}
DRIVER_STOPS: dict[str, dict[str, Any]] = {}


def _vehicle_to_response(vehicle: Vehicle) -> dict[str, Any]:
    return {
        "id": vehicle.vehicle_id,
        "name": vehicle.name,
        "status": vehicle.status or "available",
        "capacity_kg": vehicle.capacity or 0,
        "volume_m3": vehicle.volumn_m3 or 0,
        "cost_per_km": vehicle.cost_per_km or 0,
        "ev": bool(vehicle.ev),
    }


def _point_to_location_response(point: Point) -> dict[str, Any]:
    return {
        "id": point.id,
        "name": point.name,
        "address_string": point.address or "",
        "coordinates": {
            "lat": point.latitude,
            "lng": point.longitude,
        },
        "demand_kg": point.demand or 0,
        "time_window_start": point.time_window_start or "",
        "time_window_end": point.time_window_end or "",
        "service_time_mins": point.service_time or 0,
    }


def _materialize_job(job: dict[str, Any]) -> dict[str, Any]:
    if job["status"] == "calculating" and datetime.now(timezone.utc) >= job["ready_at"]:
        vehicle_ids = job["request"]["vehicles"]
        location_ids = job["request"]["locations"]

        planned_routes: list[dict[str, Any]] = []
        for index, vehicle_id in enumerate(vehicle_ids):
            assigned_stops = location_ids[index:: max(len(vehicle_ids), 1)]
            planned_routes.append(
                {
                    "route_id": f"route-{job['job_id']}-{index + 1}",
                    "vehicle_id": vehicle_id,
                    "stops": assigned_stops,
                    "stop_count": len(assigned_stops),
                }
            )

        job["status"] = "completed"
        job["result"] = {
            "project_id": job["request"]["project_id"],
            "objective": job["request"]["objective"],
            "solver_algorithm": job["request"]["solver_algorithm"],
            "total_distance_km": round(len(location_ids) * 2.35, 2),
            "total_duration_minutes": len(location_ids) * 18,
            "routes": planned_routes,
        }

        for planned_route in planned_routes:
            route_id = planned_route["route_id"]
            if route_id not in ROUTE_DETAILS:
                ROUTE_DETAILS[route_id] = {
                    "route_id": route_id,
                    "vehicle_id": planned_route["vehicle_id"],
                    "status": "planned",
                    "stops": planned_route["stops"],
                    "metrics": {
                        "total_distance_km": round(max(planned_route["stop_count"], 1) * 2.2, 2),
                        "total_duration_minutes": planned_route["stop_count"] * 20,
                        "stop_count": planned_route["stop_count"],
                        "completed_stops": 0,
                    },
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
    return job


def _extract_row(row: pd.Series, candidates: list[str], default: Any = None) -> Any:
    for key in candidates:
        if key in row and pd.notna(row[key]):
            return row[key]
    return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _serialize_job(job: dict[str, Any]) -> dict[str, Any]:
    materialized = _materialize_job(job)
    return {
        "job_id": materialized["job_id"],
        "status": materialized["status"],
        "created_at": materialized["created_at"].isoformat(),
        "estimated_time_seconds": materialized["estimated_time_seconds"],
    }


def _route_summary(route_detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "route_id": route_detail["route_id"],
        "vehicle_id": route_detail["vehicle_id"],
        "status": route_detail["status"],
        "stop_count": route_detail["metrics"]["stop_count"],
        "total_distance_km": route_detail["metrics"]["total_distance_km"],
        "total_duration_minutes": route_detail["metrics"]["total_duration_minutes"],
    }


def _normalize_route_detail(route_id: str, db: Session) -> dict[str, Any]:
    route_detail = ROUTE_DETAILS.get(route_id)
    if route_detail:
        return route_detail

    route = db.query(Route).filter(Route.route_id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    generated = {
        "route_id": route.route_id,
        "vehicle_id": route.vehicle_id,
        "status": "active" if route_id in ACTIVE_ROUTES else "planned",
        "stops": [],
        "metrics": {
            "total_distance_km": _to_float(getattr(route, "total_distance", 0.0)),
            "total_duration_minutes": _to_float(getattr(route, "total_duration", 0.0)),
            "stop_count": 0,
            "completed_stops": 0,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    ROUTE_DETAILS[route_id] = generated
    return generated


def _vehicle_or_404(vehicle_id: str, db: Session) -> Vehicle:
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


def _point_or_404(location_id: str, db: Session) -> Point:
    point = db.query(Point).filter(Point.id == location_id).first()
    if not point:
        raise HTTPException(status_code=404, detail="Location not found")
    return point


@router.get("/fleet/vehicles")
def get_fleet_vehicles(db: Session = Depends(get_db)):
    vehicles = db.query(Vehicle).all()
    return [_vehicle_to_response(vehicle) for vehicle in vehicles]


@router.post("/fleet/vehicles")
def create_fleet_vehicle(payload: VehicleCreateDTO, db: Session = Depends(get_db)):
    from app.utils.validators import validate_vehicle_input
    
    # Validate input
    try:
        validate_vehicle_input(payload.name, payload.capacity_kg, payload.volume_m3)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    existing = db.query(Vehicle).filter(Vehicle.vehicle_id == payload.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Vehicle id already exists")

    vehicle = Vehicle(
        vehicle_id=payload.id,
        name=payload.name,
        status=payload.status,
        capacity=payload.capacity_kg,
        volumn_m3=int(payload.volume_m3),
        cost_per_km=payload.cost_per_km,
        ev=payload.ev,
        license_plate=payload.license_plate,
        cost_per_hour=payload.cost_per_hour,
        max_shift_hours=payload.max_shift_hours,
        depot_lat=payload.depot_lat,
        depot_lon=payload.depot_lon,
        driver_name=payload.driver_name,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return _vehicle_to_response(vehicle)


@router.get("/fleet/vehicles/{vehicle_id}")
def get_fleet_vehicle_detail(vehicle_id: str, db: Session = Depends(get_db)):
    vehicle = _vehicle_or_404(vehicle_id, db)
    return _vehicle_to_response(vehicle)


@router.put("/fleet/vehicles/{vehicle_id}")
def update_fleet_vehicle(vehicle_id: str, payload: VehicleUpdateDTO, db: Session = Depends(get_db)):
    vehicle = _vehicle_or_404(vehicle_id, db)
    updates = payload.model_dump(exclude_none=True)

    if "name" in updates:
        vehicle.name = updates["name"]
    if "status" in updates:
        vehicle.status = updates["status"]
    if "capacity_kg" in updates:
        vehicle.capacity = updates["capacity_kg"]
    if "volume_m3" in updates:
        cast(Any, vehicle).volumn_m3 = int(updates["volume_m3"])
    if "cost_per_km" in updates:
        vehicle.cost_per_km = updates["cost_per_km"]
    if "ev" in updates:
        vehicle.ev = updates["ev"]
    if "license_plate" in updates:
        vehicle.license_plate = updates["license_plate"]
    if "cost_per_hour" in updates:
        vehicle.cost_per_hour = updates["cost_per_hour"]
    if "max_shift_hours" in updates:
        vehicle.max_shift_hours = updates["max_shift_hours"]
    if "depot_lat" in updates:
        vehicle.depot_lat = updates["depot_lat"]
    if "depot_lon" in updates:
        vehicle.depot_lon = updates["depot_lon"]
    if "driver_name" in updates:
        vehicle.driver_name = updates["driver_name"]

    db.commit()
    db.refresh(vehicle)
    return _vehicle_to_response(vehicle)


@router.delete("/fleet/vehicles/{vehicle_id}")
def delete_fleet_vehicle(vehicle_id: str, db: Session = Depends(get_db)):
    vehicle = _vehicle_or_404(vehicle_id, db)
    
    # Check if vehicle is used in any active routes
    for active_route in ACTIVE_ROUTES.values():
        if active_route.get("vehicle_id") == vehicle_id:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete vehicle {vehicle_id}: it has active routes"
            )
    
    # Also check in database route details
    route_details_in_db = db.query(RouteDetail).filter(
        RouteDetail.vehicle_id == vehicle_id
    ).all()
    
    for route_detail in route_details_in_db:
        if route_detail.status in ["planned", "active"]:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete vehicle {vehicle_id}: it has active routes"
            )
    
    db.delete(vehicle)
    db.commit()
    return {
        "success": True,
        "deleted_id": vehicle_id,
    }


@router.get("/locations/demand")
def get_location_demand(db: Session = Depends(get_db)):
    points = db.query(Point).all()
    return [_point_to_location_response(point) for point in points]


@router.post("/locations")
def create_location(payload: LocationCreateDTO, db: Session = Depends(get_db)):
    from app.utils.validators import validate_location_input
    
    # Validate input
    try:
        validate_location_input(payload.name, payload.lat, payload.lng, payload.demand_kg)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    location_id = payload.id or f"loc-{uuid4().hex[:8]}"
    existing = db.query(Point).filter(Point.id == location_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Location id already exists")

    point = Point(
        id=location_id,
        name=payload.name,
        address=payload.address_string,
        latitude=payload.lat,
        longitude=payload.lng,
        demand=payload.demand_kg,
        priority=payload.priority,
        phone=payload.phone,
        time_window_start=payload.time_window_start,
        time_window_end=payload.time_window_end,
        service_time=payload.service_time_mins,
    )
    db.add(point)
    db.commit()
    db.refresh(point)
    return _point_to_location_response(point)


@router.get("/locations/{location_id}")
def get_location_detail(location_id: str, db: Session = Depends(get_db)):
    point = _point_or_404(location_id, db)
    return _point_to_location_response(point)


@router.put("/locations/{location_id}")
def update_location(location_id: str, payload: LocationUpdateDTO, db: Session = Depends(get_db)):
    from app.utils.validators import validate_coordinates, validate_demand
    
    point = _point_or_404(location_id, db)
    updates = payload.model_dump(exclude_none=True)

    # Validate updates if coordinates or demand provided
    if "lat" in updates and "lng" in updates:
        try:
            validate_coordinates(updates["lat"], updates["lng"])
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    if "demand_kg" in updates:
        try:
            validate_demand(updates["demand_kg"])
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    if "name" in updates:
        point.name = updates["name"]
    if "address_string" in updates:
        point.address = updates["address_string"]
    if "lat" in updates:
        point.latitude = updates["lat"]
    if "lng" in updates:
        point.longitude = updates["lng"]
    if "demand_kg" in updates:
        point.demand = updates["demand_kg"]
    if "priority" in updates:
        point.priority = updates["priority"]
    if "phone" in updates:
        point.phone = updates["phone"]
    if "time_window_start" in updates:
        point.time_window_start = updates["time_window_start"]
    if "time_window_end" in updates:
        point.time_window_end = updates["time_window_end"]
    if "service_time_mins" in updates:
        point.service_time = updates["service_time_mins"]

    db.commit()
    db.refresh(point)
    return _point_to_location_response(point)


@router.delete("/locations/{location_id}")
def delete_location(location_id: str, db: Session = Depends(get_db)):
    point = _point_or_404(location_id, db)
    
    # Check if location is used in any route details (from in-memory ROUTE_DETAILS)
    for route_detail in ROUTE_DETAILS.values():
        if location_id in route_detail.get("stops", []):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete location {location_id}: it is used in active routes"
            )
    
    # Also check in database route details if they exist
    route_details_in_db = db.query(RouteDetail).all()
    for route_detail in route_details_in_db:
        stops_list = route_detail.stops or []
        if isinstance(stops_list, list) and location_id in stops_list:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete location {location_id}: it is used in active routes"
            )
    
    db.delete(point)
    db.commit()
    return {
        "success": True,
        "deleted_id": location_id,
    }


@router.post("/optimize/run")
def run_optimizer(payload: OptimizeRunRequestDTO):
    job_id = f"job-{uuid4().hex[:8]}"
    estimated_time = max(1.5, min(30.0, len(payload.locations) * 0.5))

    job_data = {
        "job_id": job_id,
        "status": "calculating",
        "request": payload.model_dump(),
        "created_at": datetime.now(timezone.utc),
        "ready_at": datetime.now(timezone.utc) + timedelta(seconds=estimated_time),
        "estimated_time_seconds": estimated_time,
        "result": None,
    }
    OPTIMIZATION_JOBS[job_id] = job_data

    return {
        "job_id": job_id,
        "status": "calculating",
        "estimated_time_seconds": estimated_time,
    }


@router.get("/optimize/job/{job_id}")
def get_optimizer_job(job_id: str):
    job = OPTIMIZATION_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    materialized = _materialize_job(job)
    response = {
        "job_id": materialized["job_id"],
        "status": materialized["status"],
    }
    if materialized["status"] == "completed":
        response["result"] = materialized["result"]
    return response


@router.get("/optimize/jobs")
def get_optimizer_jobs():
    jobs = [_serialize_job(job) for job in OPTIMIZATION_JOBS.values()]
    return sorted(jobs, key=lambda item: item["created_at"], reverse=True)


@router.post("/optimize/job/{job_id}/cancel")
def cancel_optimizer_job(job_id: str):
    job = OPTIMIZATION_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check current status without materializing (to avoid side effects)
    current_status = job.get("status")
    
    if current_status == "completed":
        raise HTTPException(status_code=409, detail="Completed job cannot be cancelled")
    
    if current_status == "cancelled":
        raise HTTPException(status_code=409, detail="Job is already cancelled")
    
    # Update job status directly - atomic operation
    job["status"] = "cancelled"
    
    return {
        "success": True,
        "job_id": job_id,
        "status": "cancelled",
    }


@router.get("/optimize/job/{job_id}/result")
def get_optimizer_job_result(job_id: str):
    job = OPTIMIZATION_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    materialized = _materialize_job(job)
    if materialized["status"] != "completed":
        raise HTTPException(status_code=409, detail="Job result is not available yet")

    return materialized["result"]


@router.get("/routes/active")
def get_active_routes(db: Session = Depends(get_db)):
    # First try to get from in-memory cache
    if ACTIVE_ROUTES:
        return list(ACTIVE_ROUTES.values())

    # If no in-memory routes, try querying database active_routes table
    from app.repositories.active_route_repository import get_all_active_routes as get_db_active_routes
    db_active_routes = get_db_active_routes(db)
    
    result = []
    for route in db_active_routes:
        result.append({
            "route_id": route.route_id,
            "vehicle_id": route.vehicle_id,
            "driver_name": route.driver_name or "Unknown",
            "status": route.status,
            "progress_percentage": route.progress_percentage,
            "current_coordinates": {
                "lat": route.current_lat,
                "lng": route.current_lng,
            },
            "next_stop": {
                "location_id": route.next_location_id,
                "name": route.next_location_name,
                "eta": route.next_eta,
                "stop_index": route.next_stop_index,
                "total_stops": route.total_stops,
            },
            "delay_mins": route.delay_mins,
        })
    
    # If still no routes found, return empty array with proper format
    if not result:
        # Optionally try Route table as fallback
        routes = db.query(Route).all()
        if routes:
            return [{
                "route_id": route.route_id,
                "vehicle_id": route.vehicle_id,
                "driver_name": "Unknown",
                "status": "on-time",
                "progress_percentage": 0,
                "current_coordinates": {"lat": 0.0, "lng": 0.0},
                "next_stop": {
                    "location_id": None,
                    "name": None,
                    "eta": None,
                    "stop_index": 0,
                    "total_stops": 0,
                },
                "delay_mins": 0,
            } for route in routes]
    
    return result


@router.get("/routes")
def list_routes(db: Session = Depends(get_db)):
    for job in OPTIMIZATION_JOBS.values():
        _materialize_job(job)

    summaries: dict[str, dict[str, Any]] = {}

    for route_detail in ROUTE_DETAILS.values():
        summaries[route_detail["route_id"]] = _route_summary(route_detail)

    for route in db.query(Route).all():
        route_id = str(getattr(route, "route_id"))
        if route_id not in summaries:
            detail = _normalize_route_detail(route_id, db)
            summaries[route_id] = _route_summary(detail)

    return list(summaries.values())


@router.get("/routes/{route_id}")
def get_route_detail(route_id: str, db: Session = Depends(get_db)):
    route_detail = _normalize_route_detail(route_id, db)
    if route_id in ACTIVE_ROUTES:
        route_detail["status"] = "active"

    return route_detail


@router.get("/routes/{route_id}/manifest")
def get_route_manifest(route_id: str, db: Session = Depends(get_db)):
    route_detail = _normalize_route_detail(route_id, db)

    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == route_detail["vehicle_id"]).first()
    stops_payload: list[dict[str, Any]] = []
    for index, stop_id in enumerate(route_detail["stops"]):
        point = db.query(Point).filter(Point.id == stop_id).first()
        stops_payload.append(
            {
                "stop_id": stop_id,
                "name": point.name if point else "Unknown",
                "address": point.address if point else "",
                "sequence": index + 1,
                "status": DRIVER_STOPS.get(stop_id, {}).get("status", "pending"),
            }
        )

    return {
        "route_id": route_id,
        "vehicle_id": route_detail["vehicle_id"],
        "driver_name": vehicle.driver_name if vehicle else "Unknown",
        "status": route_detail["status"],
        "stops": stops_payload,
    }


@router.post("/routes/{route_id}/dispatch")
def dispatch_route(route_id: str, db: Session = Depends(get_db)):
    route = db.query(Route).filter(Route.route_id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == route.vehicle_id).first()

    active_record = {
        "route_id": route.route_id,
        "vehicle_id": route.vehicle_id,
        "driver_name": vehicle.driver_name if vehicle else "Unknown",
        "status": "on-time",
        "progress_percentage": 0,
        "current_coordinates": {
            "lat": vehicle.depot_lat if vehicle and vehicle.depot_lat is not None else 0.0,
            "lng": vehicle.depot_lon if vehicle and vehicle.depot_lon is not None else 0.0,
        },
        "next_stop": {
            "location_id": None,
            "name": "Start route",
            "eta": None,
            "stop_index": 0,
            "total_stops": 0,
        },
        "delay_mins": 0,
    }
    ACTIVE_ROUTES[route_id] = active_record

    route_detail = _normalize_route_detail(route_id, db)
    route_detail["status"] = "active"
    route_detail["updated_at"] = datetime.now(timezone.utc).isoformat()

    return {
        "success": True,
        "message": "Route dispatched",
        "data": active_record,
    }


@router.post("/routes/{route_id}/complete")
def complete_route(route_id: str, db: Session = Depends(get_db)):
    route_detail = _normalize_route_detail(route_id, db)
    route_detail["status"] = "completed"
    route_detail["metrics"]["completed_stops"] = route_detail["metrics"]["stop_count"]
    route_detail["updated_at"] = datetime.now(timezone.utc).isoformat()

    if route_id in ACTIVE_ROUTES:
        del ACTIVE_ROUTES[route_id]

    return {
        "success": True,
        "route_id": route_id,
        "status": route_detail["status"],
    }


@router.post("/routes/{route_id}/status")
def update_route_status(route_id: str, payload: RouteStatusUpdateDTO, db: Session = Depends(get_db)):
    route_detail = _normalize_route_detail(route_id, db)
    route_detail["status"] = payload.status
    route_detail["updated_at"] = datetime.now(timezone.utc).isoformat()

    if payload.note:
        route_detail["status_note"] = payload.note

    if payload.status == "completed" and route_id in ACTIVE_ROUTES:
        del ACTIVE_ROUTES[route_id]

    return {
        "success": True,
        "data": route_detail,
    }


@router.get("/metrics/dashboard")
def get_dashboard_metrics(db: Session = Depends(get_db)):
    routes = db.query(Route).all()
    vehicles = db.query(Vehicle).all()

    total_active = len(ACTIVE_ROUTES)
    utilization = 0.0
    if vehicles:
        utilization = round((total_active / len(vehicles)) * 100, 2)

    distance_values = [getattr(route, "total_distance", 0) for route in routes]
    total_distance = round(sum(float(value or 0) for value in distance_values), 2)
    cost_savings = round(total_distance * 0.13, 2)
    trend_base = int(utilization) if utilization else 80

    return {
        "total_active_routes": total_active,
        "vehicle_utilization_pct": utilization,
        "total_distance_km": total_distance,
        "cost_savings_usd": cost_savings,
        "efficiency_trend": [trend_base - 2, trend_base, trend_base - 1, trend_base + 1],
    }


@router.get("/metrics/routes/{route_id}")
def get_route_metrics(route_id: str, db: Session = Depends(get_db)):
    route_detail = _normalize_route_detail(route_id, db)
    metrics = route_detail["metrics"]
    stop_count = max(int(metrics["stop_count"]), 1)
    completed_stops = int(metrics["completed_stops"])
    completion_pct = round((completed_stops / stop_count) * 100, 2)

    return {
        "route_id": route_id,
        "status": route_detail["status"],
        "total_distance_km": metrics["total_distance_km"],
        "total_duration_minutes": metrics["total_duration_minutes"],
        "stop_count": metrics["stop_count"],
        "completed_stops": metrics["completed_stops"],
        "completion_pct": completion_pct,
    }


@router.get("/reports/routes/{route_id}")
def get_route_report(route_id: str, db: Session = Depends(get_db)):
    route_detail = _normalize_route_detail(route_id, db)
    metrics = get_route_metrics(route_id, db)

    return {
        "route": {
            "route_id": route_id,
            "vehicle_id": route_detail["vehicle_id"],
            "status": route_detail["status"],
        },
        "metrics": metrics,
        "stops": route_detail["stops"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/reports/routes/{route_id}/export")
def export_route_report(
    route_id: str,
    format: str = Query("json", pattern="^(pdf|xlsx|json)$"),
    db: Session = Depends(get_db),
):
    report = get_route_report(route_id, db)

    if format == "json":
        return report

    if format == "xlsx":
        lines = [
            "route_id\tvehicle_id\tstatus\ttotal_distance_km\ttotal_duration_minutes\tstop_count\tcompleted_stops",
            (
                f"{report['route']['route_id']}\t{report['route']['vehicle_id']}\t{report['route']['status']}\t"
                f"{report['metrics']['total_distance_km']}\t{report['metrics']['total_duration_minutes']}\t"
                f"{report['metrics']['stop_count']}\t{report['metrics']['completed_stops']}"
            ),
        ]
        data = "\n".join(lines).encode("utf-8")
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=route-{route_id}.xlsx"},
        )

    pdf_text = (
        f"Route Report\n"
        f"Route ID: {report['route']['route_id']}\n"
        f"Vehicle ID: {report['route']['vehicle_id']}\n"
        f"Status: {report['route']['status']}\n"
        f"Distance: {report['metrics']['total_distance_km']} km\n"
        f"Duration: {report['metrics']['total_duration_minutes']} mins\n"
    )
    return StreamingResponse(
        io.BytesIO(pdf_text.encode("utf-8")),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=route-{route_id}.pdf"},
    )


@router.post("/locations/depots")
def create_depot(payload: DepotCreateDTO, db: Session = Depends(get_db)):
    from app.models.depot import Depot
    from app.repositories.depot_repository import create_depot as repo_create_depot
    
    depot_id = f"depot-{uuid4().hex[:8]}"
    depot = Depot(
        id=depot_id,
        name=payload.name,
        lat=payload.coordinates.lat,
        lng=payload.coordinates.lng,
        operating_windows=payload.operating_windows or [],
    )
    created = repo_create_depot(db, depot)
    
    return {
        "id": created.id,
        "name": created.name,
        "coordinates": {
            "lat": created.lat,
            "lng": created.lng,
        },
        "operating_windows": created.operating_windows,
    }


@router.get("/locations/depots")
def list_depots(db: Session = Depends(get_db)):
    from app.repositories.depot_repository import get_all_depots
    
    depots = get_all_depots(db)
    return [
        {
            "id": depot.id,
            "name": depot.name,
            "coordinates": {
                "lat": depot.lat,
                "lng": depot.lng,
            },
            "operating_windows": depot.operating_windows,
        }
        for depot in depots
    ]


@router.get("/locations/depots/{depot_id}")
def get_depot(depot_id: str, db: Session = Depends(get_db)):
    from app.repositories.depot_repository import get_depot_by_id
    
    depot = get_depot_by_id(db, depot_id)
    if not depot:
        raise HTTPException(status_code=404, detail="Depot not found")
    
    return {
        "id": depot.id,
        "name": depot.name,
        "coordinates": {
            "lat": depot.lat,
            "lng": depot.lng,
        },
        "operating_windows": depot.operating_windows,
    }


@router.put("/locations/depots/{depot_id}")
def update_depot(depot_id: str, payload: DepotUpdateDTO, db: Session = Depends(get_db)):
    from app.repositories.depot_repository import update_depot as repo_update_depot
    
    updates = {}
    if payload.name is not None:
        updates["name"] = payload.name
    if payload.coordinates is not None:
        updates["lat"] = payload.coordinates.lat
        updates["lng"] = payload.coordinates.lng
    if payload.operating_windows is not None:
        updates["operating_windows"] = payload.operating_windows
    
    depot = repo_update_depot(db, depot_id, updates)
    if not depot:
        raise HTTPException(status_code=404, detail="Depot not found")
    
    return {
        "id": depot.id,
        "name": depot.name,
        "coordinates": {
            "lat": depot.lat,
            "lng": depot.lng,
        },
        "operating_windows": depot.operating_windows,
    }


@router.delete("/locations/depots/{depot_id}")
def delete_depot(depot_id: str, db: Session = Depends(get_db)):
    from app.repositories.depot_repository import delete_depot as repo_delete_depot
    
    depot = repo_delete_depot(db, depot_id)
    if not depot:
        raise HTTPException(status_code=404, detail="Depot not found")
    
    return {
        "success": True,
        "deleted_id": depot_id,
    }


@router.post("/users")
def create_user(payload: UserCreateDTO, db: Session = Depends(get_db)):
    from app.models.user import User as UserModel
    from app.repositories.user_repository import create_user as repo_create_user
    
    user_id = f"user-{uuid4().hex[:8]}"
    user = UserModel(
        id=user_id,
        full_name=payload.full_name,
        role=payload.role,
        phone=payload.phone,
        email=payload.email,
    )
    created = repo_create_user(db, user)
    
    return {
        "id": created.id,
        "full_name": created.full_name,
        "role": created.role,
        "phone": created.phone,
        "email": created.email,
    }


@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    from app.repositories.user_repository import get_all_users
    
    users = get_all_users(db)
    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "role": user.role,
            "phone": user.phone,
            "email": user.email,
        }
        for user in users
    ]


@router.get("/users/{user_id}")
def get_user(user_id: str, db: Session = Depends(get_db)):
    from app.repositories.user_repository import get_user_by_id
    
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "full_name": user.full_name,
        "role": user.role,
        "phone": user.phone,
        "email": user.email,
    }


@router.put("/users/{user_id}")
def update_user(user_id: str, payload: UserUpdateDTO, db: Session = Depends(get_db)):
    from app.repositories.user_repository import update_user as repo_update_user
    
    updates = payload.model_dump(exclude_none=True)
    user = repo_update_user(db, user_id, updates)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "full_name": user.full_name,
        "role": user.role,
        "phone": user.phone,
        "email": user.email,
    }


@router.delete("/users/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db)):
    from app.repositories.user_repository import delete_user as repo_delete_user
    
    user = repo_delete_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "success": True,
        "deleted_id": user_id,
    }


@router.post("/locations/upload-manifest")
async def upload_manifest(file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or ""
    extension = filename.split(".")[-1].lower() if "." in filename else ""
    content = await file.read()

    if extension == "csv":
        dataframe = pd.read_csv(io.BytesIO(content))
    elif extension in {"xlsx", "xls"}:
        dataframe = pd.read_excel(io.BytesIO(content))
    else:
        raise HTTPException(status_code=400, detail="Only .csv, .xlsx, .xls are supported")

    created_count = 0
    for _, row in dataframe.iterrows():
        point_id = str(_extract_row(row, ["id", "location_id", "stop_id"], f"loc-{uuid4().hex[:8]}"))
        existing = db.query(Point).filter(Point.id == point_id).first()
        if existing:
            continue

        point = Point(
            id=point_id,
            name=str(_extract_row(row, ["name", "location_name", "customer_name"], "Unknown")),
            address=str(_extract_row(row, ["address", "address_string"], "")),
            latitude=float(_extract_row(row, ["latitude", "lat"], 0.0)),
            longitude=float(_extract_row(row, ["longitude", "lng", "lon"], 0.0)),
            demand=int(float(_extract_row(row, ["demand", "demand_kg", "quantity"], 0))),
            priority=int(float(_extract_row(row, ["priority"], 0))),
            phone=str(_extract_row(row, ["phone"], "")),
            time_window_start=str(_extract_row(row, ["time_window_start"], "")),
            time_window_end=str(_extract_row(row, ["time_window_end"], "")),
            service_time=int(float(_extract_row(row, ["service_time", "service_time_mins"], 0))),
        )
        db.add(point)
        created_count += 1

    db.commit()

    return {
        "success": True,
        "uploaded_rows": int(dataframe.shape[0]),
        "created_locations": created_count,
        "message": "Manifest processed successfully",
    }


@router.post("/routes/{route_id}/adjust")
def adjust_route(route_id: str, payload: RouteAdjustDTO):
    adjustment = {
        "route_id": route_id,
        "stop_id": payload.stop_id,
        "source_route_id": payload.source_route_id,
        "target_route_id": payload.target_route_id,
        "new_sequence_index": payload.new_sequence_index,
        "locked": True,
    }

    target_route = ACTIVE_ROUTES.get(payload.target_route_id)
    if target_route:
        target_route["next_stop"]["location_id"] = payload.stop_id

    return {
        "success": True,
        "message": "Route adjusted",
        "data": adjustment,
    }


@router.get("/driver/manifest")
def get_driver_manifest():
    manifests: list[dict[str, Any]] = []
    for route in ACTIVE_ROUTES.values():
        manifests.append(
            {
                "route_id": route["route_id"],
                "vehicle_id": route["vehicle_id"],
                "driver_name": route["driver_name"],
                "stops": [
                    {
                        "stop_id": route["next_stop"]["location_id"],
                        "name": route["next_stop"]["name"],
                        "eta": route["next_stop"]["eta"],
                        "status": "pending",
                    }
                ],
            }
        )

    if manifests:
        return manifests

    return [
        {
            "route_id": "sample-route",
            "vehicle_id": "sample-vehicle",
            "driver_name": "Unknown",
            "stops": [],
        }
    ]


@router.get("/driver/routes/{route_id}/stops")
def get_driver_route_stops(route_id: str, db: Session = Depends(get_db)):
    route_detail = _normalize_route_detail(route_id, db)
    stops = []
    for stop_id in route_detail["stops"]:
        point = db.query(Point).filter(Point.id == stop_id).first()
        stop_status = DRIVER_STOPS.get(stop_id, {}).get("status", "pending")
        stops.append(
            {
                "stop_id": stop_id,
                "name": point.name if point else "Unknown",
                "status": stop_status,
            }
        )
    return {
        "route_id": route_id,
        "stops": stops,
    }


@router.put("/driver/stops/{stop_id}/status")
def update_driver_stop_status(stop_id: str, payload: DriverStopStatusUpdateDTO):
    DRIVER_STOPS[stop_id] = {
        "stop_id": stop_id,
        "status": payload.status,
        "proof_of_delivery_url": payload.proof_of_delivery_url,
        "notes": payload.notes,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    return {
        "success": True,
        "data": DRIVER_STOPS[stop_id],
    }


@router.get("/driver/stops/{stop_id}")
def get_driver_stop_status(stop_id: str):
    stop = DRIVER_STOPS.get(stop_id)
    if not stop:
        raise HTTPException(status_code=404, detail="Driver stop not found")
    return stop
