from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, cast

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.algorithms.cvrp_solver import solve_cvrp
from app.algorithms.genetic_algorithm_vrp import genetic_algorithm_vrp
from app.algorithms.vrp_solver import Customer, Vehicle, VRPSolution
from app.core.config import settings
from app.core.enums import JobStatus, RouteStatus, SolverAlgorithm
from app.core.ids import generate_id
from app.models.location import Location
from app.models.optimization_job import OptimizationJob
from app.models.route import Route
from app.models.route_stop import RouteStop
from app.models.vehicle import Vehicle as VehicleModel
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


def _build_vrp_data(
    vehicle_map: dict[str, VehicleModel],
    location_map: dict[str, Location],
    vehicle_ids: list[str],
    location_ids: list[str],
) -> tuple[list[Customer], list[Vehicle]]:
    """Convert DB models to VRP solver data structures."""
    # Build customers
    customers: list[Customer] = []
    for lid in location_ids:
        loc = location_map[lid]
        customers.append(Customer(
            id=lid,
            lat=float(loc.lat),
            lng=float(loc.lng),
            demand=float(loc.demand_kg or 0),
        ))

    # Build vehicles
    vrp_vehicles: list[Vehicle] = []
    for vid in vehicle_ids:
        v = vehicle_map[vid]
        depot_lat = float(v.depot.lat) if v.depot else 0.0
        depot_lng = float(v.depot.lng) if v.depot else 0.0
        vrp_vehicles.append(Vehicle(
            id=vid,
            capacity=float(v.capacity_kg or 0),
            depot_lat=depot_lat,
            depot_lng=depot_lng,
            cost_per_km=float(v.cost_per_km or 0.0),
        ))

    return customers, vrp_vehicles


def _run_vrp_solver(
    algorithm: str,
    customers: list[Customer],
    vehicles: list[Vehicle],
) -> VRPSolution:
    """Run VRP solver and return solution."""
    if algorithm in {SolverAlgorithm.GENETIC_ALGORITHM.value, "ga"}:
        return genetic_algorithm_vrp(customers, vehicles)
    else:
        # Default to sweep algorithm for nearest_neighbor
        return solve_cvrp(customers, vehicles, algorithm="sweep")


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

    # Build VRP data and solve
    customers, vrp_vehicles = _build_vrp_data(vehicle_map, location_map, vehicle_ids, location_ids)
    vrp_solution = _run_vrp_solver(algorithm, customers, vrp_vehicles)

    planned_routes: list[dict[str, Any]] = []
    total_distance_km = vrp_solution.total_distance_km
    now = datetime.now(timezone.utc)
    avg_speed = settings.DEFAULT_AVG_SPEED_KMH

    # Create routes from VRP solution
    for idx, route in enumerate(vrp_solution.routes):
        if not route.customer_ids:
            continue

        vehicle = vehicle_map[route.vehicle_id]
        ordered_stop_ids = route.customer_ids
        route_dist_km = route.total_distance_km

        load_kg = int(route.total_demand)
        capacity = int(vehicle.capacity_kg or 0)
        utilization = round((load_kg / capacity) * 100, 2) if capacity > 0 else 0.0
        cost_per_km = float(vehicle.cost_per_km or 0.0)
        total_cost = round(route_dist_km * cost_per_km, 2)
        duration_mins = round((route_dist_km / avg_speed) * 60 + len(ordered_stop_ids) * 10, 2)

        route_id = f"route-{job.id}-{idx + 1}"
        db_route = db.get(Route, route_id)
        if db_route is None:
            db_route = Route(
                id=route_id,
                job_id=cast(str, job.id),
                vehicle_id=route.vehicle_id,
                depot_id=cast(str, vehicle.depot_id),
            )
            db.add(db_route)

        db_route.status = RouteStatus.PLANNED.value
        db_route.total_distance_km = round(route_dist_km, 2)
        db_route.total_duration_mins = duration_mins
        db_route.total_cost = total_cost
        db_route.load_kg = load_kg
        db_route.utilization_pct = utilization
        db_route.updated_at = now

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
                "vehicle_id": route.vehicle_id,
                "stop_count": len(ordered_stop_ids),
                "load_kg": load_kg,
                "capacity_kg": capacity,
                "utilization_pct": utilization,
                "distance_km": round(route_dist_km, 2),
                "duration_mins": duration_mins,
                "total_cost": total_cost,
            }
        )

    # Handle unassigned customers
    result = {
        "project_id": job.project_id,
        "objective": job.objective,
        "solver_algorithm": job.solver_algorithm,
        "total_distance_km": round(total_distance_km, 2),
        "total_duration_mins": round((total_distance_km / avg_speed) * 60 + len(location_ids) * 10, 2),
        "vehicles_used": len(planned_routes),
        "routes": planned_routes,
    }

    # Handle unassigned customers
    if vrp_solution.unassigned_customers:
        result["unassigned_customers"] = vrp_solution.unassigned_customers
        result["unassigned_count"] = len(vrp_solution.unassigned_customers)

    OptimizationJobRepository(db).update(
        job,
        status=JobStatus.COMPLETED.value,
        result=result,
        completed_at=now,
    )
    return job
