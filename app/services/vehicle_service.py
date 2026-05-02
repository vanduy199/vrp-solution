from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.ids import generate_id
from app.models.vehicle import Vehicle
from app.repositories.vehicle_repo import VehicleRepository
from app.schemas.vehicle import VehicleCreate, VehicleUpdate
from app.services.depot_service import get_depot_or_404


def create_vehicle(db: Session, payload: VehicleCreate) -> Vehicle:
    if payload.depot_id:
        get_depot_or_404(db, payload.depot_id)
    if payload.driver_id:
        from app.services.driver_profile_service import get_driver_or_404
        get_driver_or_404(db, payload.driver_id)

    repo = VehicleRepository(db)
    vehicle_id = payload.id or generate_id("veh")
    if repo.get(vehicle_id):
        raise HTTPException(status_code=409, detail="Vehicle id already exists")

    vehicle = Vehicle(
        id=vehicle_id,
        name=payload.name,
        license_plate=payload.license_plate,
        status=payload.status.value,
        capacity_kg=payload.capacity_kg,
        volume_m3=payload.volume_m3,
        cost_per_km=payload.cost_per_km,
        cost_per_hour=payload.cost_per_hour,
        max_shift_hours=payload.max_shift_hours,
        ev=payload.ev,
        depot_id=payload.depot_id,
        driver_id=payload.driver_id,
    )
    return repo.create(vehicle)


def get_vehicle_or_404(db: Session, vehicle_id: str) -> Vehicle:
    vehicle = VehicleRepository(db).get(vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


def list_vehicles(db: Session) -> list[Vehicle]:
    return VehicleRepository(db).list()


def update_vehicle(db: Session, vehicle_id: str, payload: VehicleUpdate) -> Vehicle:
    vehicle = get_vehicle_or_404(db, vehicle_id)
    updates = payload.model_dump(exclude_none=True)

    if "depot_id" in updates:
        get_depot_or_404(db, updates["depot_id"])
    if "driver_id" in updates and updates["driver_id"]:
        from app.services.driver_profile_service import get_driver_or_404
        get_driver_or_404(db, updates["driver_id"])
    if "status" in updates:
        updates["status"] = updates["status"].value

    return VehicleRepository(db).update(vehicle, **updates)


def delete_vehicle(db: Session, vehicle_id: str) -> None:
    vehicle = get_vehicle_or_404(db, vehicle_id)
    repo = VehicleRepository(db)
    if repo.has_active_routes(vehicle_id):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete vehicle '{vehicle_id}': it has active routes",
        )
    repo.delete(vehicle)
