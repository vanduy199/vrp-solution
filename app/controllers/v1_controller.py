from __future__ import annotations

from datetime import datetime, timedelta, timezone
import io
from typing import Any
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dto.v1_dto import (
    DepotCreateDTO,
    DriverStopStatusUpdateDTO,
    OptimizeRunRequestDTO,
    RouteAdjustDTO,
    UserCreateDTO,
    VehicleCreateDTO,
)
from app.models.point import Point
from app.models.route import Route
from app.models.vehicle import Vehicle

router = APIRouter(prefix="/v1")

# In-memory stores for entities not yet backed by DB models.
OPTIMIZATION_JOBS: dict[str, dict[str, Any]] = {}
ACTIVE_ROUTES: dict[str, dict[str, Any]] = {}
DEPOTS: list[dict[str, Any]] = []
USERS: list[dict[str, Any]] = []
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
    return job


def _extract_row(row: pd.Series, candidates: list[str], default: Any = None) -> Any:
    for key in candidates:
        if key in row and pd.notna(row[key]):
            return row[key]
    return default


@router.get("/fleet/vehicles")
def get_fleet_vehicles(db: Session = Depends(get_db)):
    vehicles = db.query(Vehicle).all()
    return [_vehicle_to_response(vehicle) for vehicle in vehicles]


@router.post("/fleet/vehicles")
def create_fleet_vehicle(payload: VehicleCreateDTO, db: Session = Depends(get_db)):
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


@router.get("/locations/demand")
def get_location_demand(db: Session = Depends(get_db)):
    points = db.query(Point).all()
    return [_point_to_location_response(point) for point in points]


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


@router.get("/routes/active")
def get_active_routes(db: Session = Depends(get_db)):
    if ACTIVE_ROUTES:
        return list(ACTIVE_ROUTES.values())

    routes = db.query(Route).all()
    active_data: list[dict[str, Any]] = []
    for route in routes:
        active_data.append(
            {
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
            }
        )
    return active_data


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

    return {
        "success": True,
        "message": "Route dispatched",
        "data": active_record,
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


@router.post("/locations/depots")
def create_depot(payload: DepotCreateDTO):
    depot_id = f"depot-{uuid4().hex[:8]}"
    depot = {
        "id": depot_id,
        "name": payload.name,
        "coordinates": payload.coordinates.model_dump(),
        "operating_windows": payload.operating_windows,
    }
    DEPOTS.append(depot)
    return depot


@router.post("/users")
def create_user(payload: UserCreateDTO):
    user_id = f"user-{uuid4().hex[:8]}"
    user = {
        "id": user_id,
        "full_name": payload.full_name,
        "role": payload.role,
        "phone": payload.phone,
        "email": payload.email,
    }
    USERS.append(user)
    return user


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
