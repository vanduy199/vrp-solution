from __future__ import annotations

from datetime import datetime, timedelta, timezone
import io
from types import SimpleNamespace
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
from app.models.depot import Depot
from app.services.optimization_service import optimize_ga, optimize_route

router = APIRouter(prefix="/v1")


def _vehicle_to_response(vehicle: Vehicle) -> dict[str, Any]:
    return {
        "id": vehicle.vehicle_id,
        "name": vehicle.name,
        "status": vehicle.status or "available",
        "capacity_kg": vehicle.capacity or 0,
        "volume_m3": vehicle.volumn_m3 or 0,
        "cost_per_km": vehicle.cost_per_km or 0,
        "ev": bool(vehicle.ev),
        "license_plate": vehicle.license_plate,
        "cost_per_hour": vehicle.cost_per_hour,
        "max_shift_hours": vehicle.max_shift_hours,
        "depot_lat": vehicle.depot_lat,
        "depot_lon": vehicle.depot_lon,
        "driver_name": vehicle.driver_name,
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


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _materialize_db_job(job: OptimizationJob, db: Session) -> OptimizationJob:
    ready_at = _as_utc(cast(datetime, getattr(job, "ready_at")))
    status = cast(str, getattr(job, "status"))
    if status == "calculating" and datetime.now(timezone.utc) >= ready_at:
        vehicle_ids = cast(list[str], getattr(job, "vehicle_ids") or [])
        location_ids = cast(list[str], getattr(job, "location_ids") or [])
        job_id = cast(str, getattr(job, "job_id"))
        project_id = cast(str, getattr(job, "project_id"))
        objective = cast(str, getattr(job, "objective"))
        solver_algorithm = cast(str, getattr(job, "solver_algorithm"))

        if not vehicle_ids:
            setattr(job, "status", "failed")
            setattr(job, "result", {"error": "No vehicles provided"})
            db.commit()
            db.refresh(job)
            return job

        vehicles = db.query(Vehicle).filter(Vehicle.vehicle_id.in_(vehicle_ids)).all()
        vehicle_map = {cast(str, vehicle.vehicle_id): vehicle for vehicle in vehicles}
        missing_vehicle_ids = [vehicle_id for vehicle_id in vehicle_ids if vehicle_id not in vehicle_map]
        if missing_vehicle_ids:
            setattr(job, "status", "failed")
            setattr(
                job,
                "result",
                {
                    "error": "Some vehicles were not found",
                    "missing_vehicle_ids": missing_vehicle_ids,
                },
            )
            db.commit()
            db.refresh(job)
            return job

        points = db.query(Point).filter(Point.id.in_(location_ids)).all()
        point_map = {cast(str, point.id): point for point in points}
        missing_location_ids = [location_id for location_id in location_ids if location_id not in point_map]
        if missing_location_ids:
            setattr(job, "status", "failed")
            setattr(
                job,
                "result",
                {
                    "error": "Some locations were not found",
                    "missing_location_ids": missing_location_ids,
                },
            )
            db.commit()
            db.refresh(job)
            return job

        depots = db.query(Depot).all()
        default_depot = depots[0] if depots else None

        def _resolve_depot(vehicle_id: str, assigned_points: list[Point]) -> tuple[float, float, str]:
            vehicle = vehicle_map.get(vehicle_id)
            if vehicle is not None:
                vehicle_depot_lat = getattr(vehicle, "depot_lat")
                vehicle_depot_lon = getattr(vehicle, "depot_lon")
                if vehicle_depot_lat is not None and vehicle_depot_lon is not None:
                    return float(vehicle_depot_lat), float(vehicle_depot_lon), "vehicle"

            if default_depot is not None:
                depot_lat = getattr(default_depot, "lat")
                depot_lng = getattr(default_depot, "lng")
                return float(depot_lat), float(depot_lng), "global"

            center_lat = sum(float(cast(Any, point).latitude) for point in assigned_points) / len(assigned_points)
            center_lng = sum(float(cast(Any, point).longitude) for point in assigned_points) / len(assigned_points)
            return float(center_lat), float(center_lng), "centroid"

        ordered_vehicles = [vehicle_map[vehicle_id] for vehicle_id in vehicle_ids]
        assigned_by_vehicle: dict[str, list[str]] = {vehicle_id: [] for vehicle_id in vehicle_ids}
        vehicle_loads: dict[str, int] = {vehicle_id: 0 for vehicle_id in vehicle_ids}

        capacity_by_vehicle: dict[str, int] = {}
        for vehicle in ordered_vehicles:
            vehicle_id = cast(str, vehicle.vehicle_id)
            raw_capacity = getattr(vehicle, "capacity")
            capacity_by_vehicle[vehicle_id] = int(raw_capacity or 0)

        # Greedy assignment by demand so vehicle capacity is part of the optimization flow.
        sorted_location_ids = sorted(
            location_ids,
            key=lambda location_id: (
                int(getattr(point_map[location_id], "demand") or 0),
                int(getattr(point_map[location_id], "priority") or 0),
            ),
            reverse=True,
        )

        forced_overload_assignments: list[dict[str, Any]] = []
        for location_id in sorted_location_ids:
            demand = int(getattr(point_map[location_id], "demand") or 0)

            fitting_vehicle_ids = []
            for vehicle_id in vehicle_ids:
                vehicle_capacity = capacity_by_vehicle.get(vehicle_id, 0)
                projected_load = vehicle_loads[vehicle_id] + demand
                if vehicle_capacity <= 0 or projected_load <= vehicle_capacity:
                    fitting_vehicle_ids.append(vehicle_id)

            if fitting_vehicle_ids:
                target_vehicle_id = min(
                    fitting_vehicle_ids,
                    key=lambda candidate_id: (
                        vehicle_loads[candidate_id],
                        -capacity_by_vehicle.get(candidate_id, 0),
                    ),
                )
            else:
                target_vehicle_id = min(vehicle_ids, key=lambda candidate_id: vehicle_loads[candidate_id])
                forced_overload_assignments.append(
                    {
                        "location_id": location_id,
                        "demand_kg": demand,
                        "vehicle_id": target_vehicle_id,
                        "capacity_kg": capacity_by_vehicle.get(target_vehicle_id, 0),
                        "projected_load_kg": vehicle_loads[target_vehicle_id] + demand,
                    }
                )

            assigned_by_vehicle[target_vehicle_id].append(location_id)
            vehicle_loads[target_vehicle_id] += demand

        def _solve_route(vehicle_id: str, assigned_ids: list[str]) -> tuple[list[str], float, dict[str, Any]]:
            if not assigned_ids:
                return [], 0.0, {"source": "none", "lat": None, "lng": None}

            assigned_points = [point_map[location_id] for location_id in assigned_ids]
            if len(assigned_points) == 1:
                depot_lat, depot_lng, depot_source = _resolve_depot(vehicle_id, assigned_points)
                return [cast(str, assigned_points[0].id)], 0.0, {
                    "source": depot_source,
                    "lat": round(depot_lat, 6),
                    "lng": round(depot_lng, 6),
                }

            depot_lat, depot_lng, depot_source = _resolve_depot(vehicle_id, assigned_points)
            depot = SimpleNamespace(id="__depot__", latitude=depot_lat, longitude=depot_lng)
            solver_points = [depot, *assigned_points]

            algorithm_key = solver_algorithm.strip().lower()
            if algorithm_key in {"genetic_algorithm", "ga"}:
                solver_output = optimize_ga(solver_points)
            else:
                solver_output = optimize_route(solver_points)

            raw_route = cast(list[int], solver_output.get("route", []))
            normalized_indices: list[int] = []
            for point_index in raw_route:
                if isinstance(point_index, int) and 1 <= point_index < len(solver_points):
                    normalized_indices.append(point_index)

            ordered_indices: list[int] = []
            visited_indices: set[int] = set()
            for point_index in normalized_indices:
                if point_index not in visited_indices:
                    visited_indices.add(point_index)
                    ordered_indices.append(point_index)
            for point_index in range(1, len(solver_points)):
                if point_index not in visited_indices:
                    ordered_indices.append(point_index)

            ordered_stop_ids = [cast(str, solver_points[point_index].id) for point_index in ordered_indices]
            route_distance = float(solver_output.get("total_distance", 0.0) or 0.0)
            return ordered_stop_ids, route_distance, {
                "source": depot_source,
                "lat": round(depot_lat, 6),
                "lng": round(depot_lng, 6),
            }

        planned_routes: list[dict[str, Any]] = []
        total_distance_km = 0.0
        for index, vehicle_id in enumerate(vehicle_ids):
            assigned_location_ids = assigned_by_vehicle.get(vehicle_id, [])
            ordered_stops, route_distance_km, depot_info = _solve_route(vehicle_id, assigned_location_ids)
            route_duration_minutes = round((route_distance_km / 35.0) * 60 + len(ordered_stops) * 10, 2)
            vehicle_capacity = capacity_by_vehicle.get(vehicle_id, 0)
            vehicle_load = vehicle_loads.get(vehicle_id, 0)
            utilization_pct = 0.0
            if vehicle_capacity > 0:
                utilization_pct = round((vehicle_load / vehicle_capacity) * 100, 2)

            total_distance_km += route_distance_km
            planned_routes.append(
                {
                    "route_id": f"route-{job_id}-{index + 1}",
                    "vehicle_id": vehicle_id,
                    "stops": ordered_stops,
                    "stop_count": len(ordered_stops),
                    "load_kg": vehicle_load,
                    "capacity_kg": vehicle_capacity,
                    "utilization_pct": utilization_pct,
                    "depot": depot_info,
                    "distance_km": round(route_distance_km, 2),
                    "duration_minutes": route_duration_minutes,
                }
            )

        total_duration_minutes = round((total_distance_km / 35.0) * 60 + len(location_ids) * 10, 2)

        now_utc = datetime.now(timezone.utc)
        for planned_route in planned_routes:
            route_id = cast(str, planned_route["route_id"])
            vehicle_id = cast(str, planned_route["vehicle_id"])
            distance_km = float(planned_route["distance_km"])
            duration_minutes = float(planned_route["duration_minutes"])
            stop_count = int(planned_route["stop_count"])
            stops = cast(list[str], planned_route["stops"])

            vehicle_record = vehicle_map.get(vehicle_id)
            cost_per_km = 0.0
            if vehicle_record is not None:
                cost_per_km = float(getattr(vehicle_record, "cost_per_km") or 0.0)

            route_record = db.query(Route).filter(Route.route_id == route_id).first()
            if route_record is None:
                route_record = Route(route_id=route_id)
                db.add(route_record)

            setattr(route_record, "vehicle_id", vehicle_id)
            setattr(route_record, "total_distance", distance_km)
            setattr(route_record, "total_duration", duration_minutes)
            setattr(route_record, "total_cost", round(distance_km * cost_per_km, 2))

            route_detail_record = db.query(RouteDetail).filter(RouteDetail.route_id == route_id).first()
            if route_detail_record is None:
                route_detail_record = RouteDetail(route_id=route_id)
                db.add(route_detail_record)
                setattr(route_detail_record, "created_at", now_utc)

            setattr(route_detail_record, "vehicle_id", vehicle_id)
            setattr(route_detail_record, "status", "planned")
            setattr(route_detail_record, "stops", stops)
            setattr(route_detail_record, "total_distance_km", distance_km)
            setattr(route_detail_record, "total_duration_minutes", duration_minutes)
            setattr(route_detail_record, "stop_count", stop_count)
            setattr(route_detail_record, "completed_stops", 0)
            setattr(route_detail_record, "updated_at", now_utc)

        setattr(job, "status", "completed")
        setattr(
            job,
            "result",
            {
                "project_id": project_id,
                "objective": objective,
                "solver_algorithm": solver_algorithm,
                "total_distance_km": round(total_distance_km, 2),
                "total_duration_minutes": total_duration_minutes,
                "forced_overload_assignments": forced_overload_assignments,
                "routes": planned_routes,
            },
        )
        db.commit()
        db.refresh(job)

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


def _serialize_db_job(job: OptimizationJob) -> dict[str, Any]:
    return {
        "job_id": cast(str, getattr(job, "job_id")),
        "status": cast(str, getattr(job, "status")),
        "created_at": _as_utc(cast(datetime, getattr(job, "created_at"))).isoformat(),
        "estimated_time_seconds": cast(float, getattr(job, "estimated_time_seconds")),
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


def _route_detail_model_to_dict(route_detail: RouteDetail) -> dict[str, Any]:
    return {
        "route_id": cast(str, route_detail.route_id),
        "vehicle_id": cast(str, route_detail.vehicle_id),
        "status": cast(str, route_detail.status),
        "stops": cast(list[str], route_detail.stops or []),
        "metrics": {
            "total_distance_km": float(getattr(route_detail, "total_distance_km") or 0.0),
            "total_duration_minutes": float(getattr(route_detail, "total_duration_minutes") or 0.0),
            "stop_count": int(getattr(route_detail, "stop_count") or 0),
            "completed_stops": int(getattr(route_detail, "completed_stops") or 0),
        },
        "created_at": _as_utc(cast(datetime, route_detail.created_at)).isoformat(),
        "updated_at": _as_utc(cast(datetime, route_detail.updated_at)).isoformat(),
    }


def _normalize_route_detail(route_id: str, db: Session) -> dict[str, Any]:
    route_detail_record = db.query(RouteDetail).filter(RouteDetail.route_id == route_id).first()
    if route_detail_record:
        return _route_detail_model_to_dict(route_detail_record)

    route = db.query(Route).filter(Route.route_id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    active_route = db.query(ActiveRoute).filter(ActiveRoute.route_id == route_id).first()
    generated_status = "active" if active_route else "planned"
    now_utc = datetime.now(timezone.utc)

    generated_record = RouteDetail(
        route_id=cast(str, route.route_id),
        vehicle_id=cast(str, route.vehicle_id),
        status=generated_status,
        stops=[],
        total_distance_km=_to_float(getattr(route, "total_distance", 0.0)),
        total_duration_minutes=_to_float(getattr(route, "total_duration", 0.0)),
        stop_count=0,
        completed_stops=0,
        created_at=now_utc,
        updated_at=now_utc,
    )
    db.add(generated_record)
    db.commit()
    db.refresh(generated_record)
    return _route_detail_model_to_dict(generated_record)


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
    active_route_record = db.query(ActiveRoute).filter(ActiveRoute.vehicle_id == vehicle_id).first()
    if active_route_record:
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

    # Check database route details to avoid deleting locations used by existing routes.
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
def run_optimizer(payload: OptimizeRunRequestDTO, db: Session = Depends(get_db)):
    job_id = f"job-{uuid4().hex[:8]}"
    estimated_time = max(1.5, min(30.0, len(payload.locations) * 0.5))
    created_at = datetime.now(timezone.utc)
    ready_at = created_at + timedelta(seconds=estimated_time)

    job = OptimizationJob(
        job_id=job_id,
        status="calculating",
        project_id=payload.project_id,
        solver_algorithm=payload.solver_algorithm,
        objective=payload.objective,
        vehicle_ids=payload.vehicles,
        location_ids=payload.locations,
        constraints=payload.constraints,
        estimated_time_seconds=estimated_time,
        created_at=created_at,
        ready_at=ready_at,
        result=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "job_id": job_id,
        "status": "calculating",
        "estimated_time_seconds": estimated_time,
    }


@router.get("/optimize/job/{job_id}")
def get_optimizer_job(job_id: str, db: Session = Depends(get_db)):
    db_job = db.query(OptimizationJob).filter(OptimizationJob.job_id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")

    materialized = _materialize_db_job(db_job, db)
    materialized_status = cast(str, getattr(materialized, "status"))
    response = {
        "job_id": cast(str, getattr(materialized, "job_id")),
        "status": materialized_status,
    }
    if materialized_status in {"completed", "failed"}:
        response["result"] = getattr(materialized, "result")
    return response


@router.get("/optimize/jobs")
def get_optimizer_jobs(db: Session = Depends(get_db)):
    db_jobs = db.query(OptimizationJob).all()
    for db_job in db_jobs:
        _materialize_db_job(db_job, db)

    jobs = [_serialize_db_job(db_job) for db_job in db_jobs]

    return sorted(jobs, key=lambda item: item["created_at"], reverse=True)


@router.post("/optimize/job/{job_id}/cancel")
def cancel_optimizer_job(job_id: str, db: Session = Depends(get_db)):
    db_job = db.query(OptimizationJob).filter(OptimizationJob.job_id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")

    db_status = cast(str, getattr(db_job, "status"))
    if db_status == "completed":
        raise HTTPException(status_code=409, detail="Completed job cannot be cancelled")
    if db_status == "cancelled":
        raise HTTPException(status_code=409, detail="Job is already cancelled")

    setattr(db_job, "status", "cancelled")
    db.commit()

    return {
        "success": True,
        "job_id": job_id,
        "status": "cancelled",
    }


@router.get("/optimize/job/{job_id}/result")
def get_optimizer_job_result(job_id: str, db: Session = Depends(get_db)):
    db_job = db.query(OptimizationJob).filter(OptimizationJob.job_id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")

    materialized = _materialize_db_job(db_job, db)
    materialized_status = cast(str, getattr(materialized, "status"))
    if materialized_status != "completed":
        raise HTTPException(status_code=409, detail="Job result is not available yet")
    return getattr(materialized, "result")


@router.get("/routes/active")
def get_active_routes(db: Session = Depends(get_db)):
    db_active_routes = db.query(ActiveRoute).all()
    
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
    
    return result


@router.get("/routes")
def list_routes(db: Session = Depends(get_db)):
    for db_job in db.query(OptimizationJob).all():
        _materialize_db_job(db_job, db)

    summaries: dict[str, dict[str, Any]] = {}

    for route_detail in db.query(RouteDetail).all():
        summaries[cast(str, route_detail.route_id)] = _route_summary(_route_detail_model_to_dict(route_detail))

    for route in db.query(Route).all():
        route_id = str(getattr(route, "route_id"))
        if route_id not in summaries:
            detail = _normalize_route_detail(route_id, db)
            summaries[route_id] = _route_summary(detail)

    return list(summaries.values())


@router.get("/routes/{route_id}")
def get_route_detail(route_id: str, db: Session = Depends(get_db)):
    route_detail = _normalize_route_detail(route_id, db)
    active_route = db.query(ActiveRoute).filter(ActiveRoute.route_id == route_id).first()
    if active_route:
        route_detail["status"] = "active"

    return route_detail


@router.get("/routes/{route_id}/manifest")
def get_route_manifest(route_id: str, db: Session = Depends(get_db)):
    route_detail = _normalize_route_detail(route_id, db)

    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == route_detail["vehicle_id"]).first()
    stops_payload: list[dict[str, Any]] = []
    for index, stop_id in enumerate(route_detail["stops"]):
        point = db.query(Point).filter(Point.id == stop_id).first()
        driver_stop = db.query(DriverStop).filter(DriverStop.stop_id == stop_id).first()
        stops_payload.append(
            {
                "stop_id": stop_id,
                "name": point.name if point else "Unknown",
                "address": point.address if point else "",
                "sequence": index + 1,
                "status": driver_stop.status if driver_stop else "pending",
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
    active_route = db.query(ActiveRoute).filter(ActiveRoute.route_id == route_id).first()
    if active_route is None:
        active_route = ActiveRoute(route_id=cast(str, route.route_id))
        db.add(active_route)

    setattr(active_route, "vehicle_id", cast(str, route.vehicle_id))
    setattr(active_route, "driver_name", active_record["driver_name"])
    setattr(active_route, "status", active_record["status"])
    setattr(active_route, "progress_percentage", active_record["progress_percentage"])
    setattr(active_route, "current_lat", active_record["current_coordinates"]["lat"])
    setattr(active_route, "current_lng", active_record["current_coordinates"]["lng"])
    setattr(active_route, "next_location_id", active_record["next_stop"]["location_id"])
    setattr(active_route, "next_location_name", active_record["next_stop"]["name"])
    setattr(active_route, "next_eta", active_record["next_stop"]["eta"])
    setattr(active_route, "next_stop_index", active_record["next_stop"]["stop_index"])
    setattr(active_route, "total_stops", active_record["next_stop"]["total_stops"])
    setattr(active_route, "delay_mins", active_record["delay_mins"])

    route_detail = _normalize_route_detail(route_id, db)
    route_detail["status"] = "active"
    route_detail["updated_at"] = datetime.now(timezone.utc).isoformat()

    route_detail_record = db.query(RouteDetail).filter(RouteDetail.route_id == route_id).first()
    if route_detail_record:
        setattr(route_detail_record, "status", "active")
        setattr(route_detail_record, "updated_at", datetime.now(timezone.utc))

    db.commit()

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

    active_route = db.query(ActiveRoute).filter(ActiveRoute.route_id == route_id).first()
    if active_route:
        db.delete(active_route)

    route_detail_record = db.query(RouteDetail).filter(RouteDetail.route_id == route_id).first()
    if route_detail_record:
        setattr(route_detail_record, "status", "completed")
        setattr(route_detail_record, "completed_stops", int(route_detail["metrics"]["stop_count"]))
        setattr(route_detail_record, "updated_at", datetime.now(timezone.utc))

    db.commit()

    return {
        "success": True,
        "route_id": route_id,
        "status": route_detail["status"],
    }



@router.delete("/routes/{route_id}")
def delete_route(route_id: str, db: Session = Depends(get_db)):
    route = db.query(Route).filter(Route.route_id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    active_route = db.query(ActiveRoute).filter(ActiveRoute.route_id == route_id).first()
    if active_route:
        db.delete(active_route)

    route_detail = db.query(RouteDetail).filter(RouteDetail.route_id == route_id).first()
    if route_detail:
        db.delete(route_detail)

    # Remove from DB
    db.delete(route)
    db.commit()

    return {"success": True, "message": f"Route {route_id} deleted"}


@router.post("/routes/{route_id}/status")
def update_route_status(route_id: str, payload: RouteStatusUpdateDTO, db: Session = Depends(get_db)):
    route_detail = _normalize_route_detail(route_id, db)
    route_detail["status"] = payload.status
    route_detail["updated_at"] = datetime.now(timezone.utc).isoformat()

    if payload.note:
        route_detail["status_note"] = payload.note

    route_detail_record = db.query(RouteDetail).filter(RouteDetail.route_id == route_id).first()
    if route_detail_record:
        setattr(route_detail_record, "status", payload.status)
        setattr(route_detail_record, "status_note", payload.note)
        setattr(route_detail_record, "updated_at", datetime.now(timezone.utc))

    if payload.status == "completed":
        active_route = db.query(ActiveRoute).filter(ActiveRoute.route_id == route_id).first()
        if active_route:
            db.delete(active_route)

    db.commit()

    return {
        "success": True,
        "data": route_detail,
    }


@router.get("/metrics/dashboard")
def get_dashboard_metrics(db: Session = Depends(get_db)):
    routes = db.query(Route).all()
    vehicles = db.query(Vehicle).all()

    total_active = db.query(ActiveRoute).count()
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
def adjust_route(route_id: str, payload: RouteAdjustDTO, db: Session = Depends(get_db)):
    adjustment = {
        "route_id": route_id,
        "stop_id": payload.stop_id,
        "source_route_id": payload.source_route_id,
        "target_route_id": payload.target_route_id,
        "new_sequence_index": payload.new_sequence_index,
        "locked": True,
    }

    target_route = db.query(ActiveRoute).filter(ActiveRoute.route_id == payload.target_route_id).first()
    if target_route:
        setattr(target_route, "next_location_id", payload.stop_id)
        setattr(target_route, "next_location_name", payload.stop_id)
        db.commit()

    return {
        "success": True,
        "message": "Route adjusted",
        "data": adjustment,
    }


@router.get("/driver/manifest")
def get_driver_manifest(db: Session = Depends(get_db)):
    manifests: list[dict[str, Any]] = []
    active_routes = db.query(ActiveRoute).all()
    for route in active_routes:
        manifests.append(
            {
                "route_id": route.route_id,
                "vehicle_id": route.vehicle_id,
                "driver_name": route.driver_name,
                "stops": [
                    {
                        "stop_id": route.next_location_id,
                        "name": route.next_location_name,
                        "eta": route.next_eta,
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
        driver_stop = db.query(DriverStop).filter(DriverStop.stop_id == stop_id).first()
        stop_status = driver_stop.status if driver_stop else "pending"
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
def update_driver_stop_status(stop_id: str, payload: DriverStopStatusUpdateDTO, db: Session = Depends(get_db)):
    stop = db.query(DriverStop).filter(DriverStop.stop_id == stop_id).first()
    if stop is None:
        stop = DriverStop(stop_id=stop_id, status=payload.status)
        db.add(stop)

    setattr(stop, "status", payload.status)
    setattr(stop, "proof_of_delivery_url", payload.proof_of_delivery_url)
    setattr(stop, "notes", payload.notes)
    setattr(stop, "updated_at", datetime.now(timezone.utc))
    db.commit()
    db.refresh(stop)

    return {
        "success": True,
        "data": {
            "stop_id": stop.stop_id,
            "status": stop.status,
            "proof_of_delivery_url": stop.proof_of_delivery_url,
            "notes": stop.notes,
            "updated_at": _as_utc(cast(datetime, stop.updated_at)).isoformat(),
        },
    }


@router.get("/driver/stops/{stop_id}")
def get_driver_stop_status(stop_id: str, db: Session = Depends(get_db)):
    stop = db.query(DriverStop).filter(DriverStop.stop_id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Driver stop not found")
    return {
        "stop_id": stop.stop_id,
        "status": stop.status,
        "proof_of_delivery_url": stop.proof_of_delivery_url,
        "notes": stop.notes,
        "updated_at": _as_utc(cast(datetime, stop.updated_at)).isoformat(),
    }
