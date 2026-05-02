from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, cast

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.algorithms.distance import build_distance_matrix
from app.algorithms.genetic_algorithm import genetic_algorithm
from app.algorithms.nearest_neighbor import nearest_neighbor
from app.core.config import settings
from app.core.enums import JobStatus, RouteStatus, SolverAlgorithm
from app.core.ids import generate_id
from app.models.location import Location
from app.models.optimization_job import OptimizationJob
from app.models.route import Route
from app.models.route_stop import RouteStop
from app.models.vehicle import Vehicle
from app.repositories.optimization_job_repo import OptimizationJobRepository
from app.schemas.optimization import OptimizeRunRequest


def create_job(db: Session, payload: OptimizeRunRequest) -> OptimizationJob:
    job_id = generate_id("job")
    estimated = max(1.5, min(30.0, len(payload.locations) * 0.5))
    now = datetime.now(timezone.utc)
    job = OptimizationJob(
        id=job_id,
        project_id=payload.project_id,
        solver_algorithm=payload.solver_algorithm.value,
        objective=payload.objective.value,
        status=JobStatus.CALCULATING.value,
        vehicle_ids=payload.vehicles,
        location_ids=payload.locations,
        constraints=payload.constraints,
        estimated_time_seconds=estimated,
        ready_at=now + timedelta(seconds=estimated),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job_or_404(db: Session, job_id: str) -> OptimizationJob:
    job = OptimizationJobRepository(db).get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def list_jobs(db: Session) -> list[OptimizationJob]:
    return OptimizationJobRepository(db).list_ordered()


def cancel_job(db: Session, job_id: str) -> OptimizationJob:
    job = get_job_or_404(db, job_id)
    status = cast(str, job.status)
    if status == JobStatus.COMPLETED.value:
        raise HTTPException(status_code=409, detail="Completed job cannot be cancelled")
    if status == JobStatus.CANCELLED.value:
        raise HTTPException(status_code=409, detail="Job is already cancelled")
    return OptimizationJobRepository(db).update(job, status=JobStatus.CANCELLED.value)


def _run_solver(algorithm: str, distance_matrix: list) -> tuple[list[int], float]:
    if algorithm in {SolverAlgorithm.GENETIC_ALGORITHM.value, "ga"}:
        route, dist = genetic_algorithm(distance_matrix)
    else:
        route, dist = nearest_neighbor(distance_matrix)
    return route, dist


def _assign_locations_to_vehicles(
    vehicle_ids: list[str],
    location_ids: list[str],
    vehicle_map: dict[str, Vehicle],
    location_map: dict[str, Location],
) -> tuple[dict[str, list[str]], dict[str, int]]:
    capacity_by_vehicle = {
        vid: int(vehicle_map[vid].capacity_kg or 0) for vid in vehicle_ids
    }
    vehicle_loads: dict[str, int] = {vid: 0 for vid in vehicle_ids}
    assigned: dict[str, list[str]] = {vid: [] for vid in vehicle_ids}

    sorted_lids = sorted(
        location_ids,
        key=lambda lid: (int(location_map[lid].demand_kg or 0), int(location_map[lid].priority or 0)),
        reverse=True,
    )

    for lid in sorted_lids:
        demand = int(location_map[lid].demand_kg or 0)
        fitting = [
            vid for vid in vehicle_ids
            if capacity_by_vehicle[vid] <= 0
            or vehicle_loads[vid] + demand <= capacity_by_vehicle[vid]
        ]
        target = min(
            fitting if fitting else vehicle_ids,
            key=lambda vid: (vehicle_loads[vid], -capacity_by_vehicle.get(vid, 0)),
        )
        assigned[target].append(lid)
        vehicle_loads[target] += demand

    return assigned, vehicle_loads


def _resolve_depot(vehicle: Vehicle | None, locations: list[Location]) -> tuple[float, float]:
    if vehicle and vehicle.depot:
        return float(vehicle.depot.lat), float(vehicle.depot.lng)
    if locations:
        return (
            sum(float(loc.lat) for loc in locations) / len(locations),
            sum(float(loc.lng) for loc in locations) / len(locations),
        )
    return 0.0, 0.0


def materialize_job(db: Session, job: OptimizationJob) -> OptimizationJob:
    if cast(str, job.status) != JobStatus.CALCULATING.value:
        return job

    ready_at = cast(datetime, job.ready_at)
    if ready_at.tzinfo is None:
        ready_at = ready_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) < ready_at:
        return job

    vehicle_ids: list[str] = list(job.vehicle_ids or [])
    location_ids: list[str] = list(job.location_ids or [])
    algorithm = cast(str, job.solver_algorithm)

    def _fail(msg: str, **extra: Any) -> OptimizationJob:
        OptimizationJobRepository(db).update(
            job, status=JobStatus.FAILED.value, result={"error": msg, **extra}
        )
        return job

    if not vehicle_ids:
        return _fail("No vehicles provided")

    vehicles = db.query(Vehicle).filter(Vehicle.id.in_(vehicle_ids)).all()
    vehicle_map = {cast(str, v.id): v for v in vehicles}
    missing_v = [vid for vid in vehicle_ids if vid not in vehicle_map]
    if missing_v:
        return _fail("Some vehicles not found", missing_vehicle_ids=missing_v)

    no_depot = [vid for vid in vehicle_ids if not vehicle_map[vid].depot_id]
    if no_depot:
        return _fail("Some vehicles have no depot assigned", vehicle_ids_without_depot=no_depot)

    locations = db.query(Location).filter(Location.id.in_(location_ids)).all()
    location_map = {cast(str, loc.id): loc for loc in locations}
    missing_l = [lid for lid in location_ids if lid not in location_map]
    if missing_l:
        return _fail("Some locations not found", missing_location_ids=missing_l)

    assigned, vehicle_loads = _assign_locations_to_vehicles(
        vehicle_ids, location_ids, vehicle_map, location_map
    )

    planned_routes: list[dict[str, Any]] = []
    total_distance_km = 0.0
    now = datetime.now(timezone.utc)
    avg_speed = settings.DEFAULT_AVG_SPEED_KMH

    for idx, vid in enumerate(vehicle_ids):
        stop_ids = assigned.get(vid, [])
        vehicle = vehicle_map[vid]

        if not stop_ids:
            continue

        stop_locs = [location_map[lid] for lid in stop_ids]
        depot_lat, depot_lng = _resolve_depot(vehicle, stop_locs)
        depot_ns = SimpleNamespace(id="__depot__", lat=depot_lat, lng=depot_lng)
        solver_points = [depot_ns, *stop_locs]

        matrix = build_distance_matrix(solver_points)
        raw_route, route_dist_km = _run_solver(algorithm, matrix)

        raw_indices = [i for i in raw_route if isinstance(i, int) and 1 <= i < len(solver_points)]
        seen: set[int] = set()
        ordered_indices: list[int] = []
        for i in raw_indices:
            if i not in seen:
                seen.add(i)
                ordered_indices.append(i)
        for i in range(1, len(solver_points)):
            if i not in seen:
                ordered_indices.append(i)

        ordered_stop_ids = [cast(str, solver_points[i].id) for i in ordered_indices]
        duration_mins = round((route_dist_km / avg_speed) * 60 + len(ordered_stop_ids) * 10, 2)
        load_kg = vehicle_loads.get(vid, 0)
        capacity = int(vehicle.capacity_kg or 0)
        utilization = round((load_kg / capacity) * 100, 2) if capacity > 0 else 0.0
        cost_per_km = float(vehicle.cost_per_km or 0.0)
        total_cost = round(route_dist_km * cost_per_km, 2)
        total_distance_km += route_dist_km

        route_id = f"route-{job.id}-{idx + 1}"
        route = db.get(Route, route_id)
        if route is None:
            route = Route(
                id=route_id,
                job_id=cast(str, job.id),
                vehicle_id=vid,
                depot_id=cast(str, vehicle.depot_id),
            )
            db.add(route)

        route.status = RouteStatus.PLANNED.value
        route.total_distance_km = round(route_dist_km, 2)
        route.total_duration_mins = duration_mins
        route.total_cost = total_cost
        route.load_kg = load_kg
        route.utilization_pct = utilization
        route.updated_at = now

        db.query(RouteStop).filter(RouteStop.route_id == route_id).delete()
        for seq, loc_id in enumerate(ordered_stop_ids):
            stop = RouteStop(
                id=generate_id("stop"),
                route_id=route_id,
                location_id=loc_id,
                sequence_index=seq,
            )
            db.add(stop)

        planned_routes.append(
            {
                "route_id": route_id,
                "vehicle_id": vid,
                "stop_count": len(ordered_stop_ids),
                "load_kg": load_kg,
                "capacity_kg": capacity,
                "utilization_pct": utilization,
                "distance_km": round(route_dist_km, 2),
                "duration_mins": duration_mins,
                "total_cost": total_cost,
            }
        )

    total_duration = round((total_distance_km / avg_speed) * 60 + len(location_ids) * 10, 2)
    result: dict[str, Any] = {
        "project_id": job.project_id,
        "objective": job.objective,
        "solver_algorithm": job.solver_algorithm,
        "total_distance_km": round(total_distance_km, 2),
        "total_duration_mins": total_duration,
        "routes": planned_routes,
    }

    OptimizationJobRepository(db).update(
        job,
        status=JobStatus.COMPLETED.value,
        result=result,
        completed_at=now,
    )
    return job
