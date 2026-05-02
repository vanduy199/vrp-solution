from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.ids import generate_ulid
from app.models.driver import Driver
from app.models.user import User
from app.repositories.driver_repo import DriverRepository
from app.schemas.driver_profile import DriverCreate, DriverUpdate
from app.services.depot_service import get_depot_or_404


def _assign_vehicle(db: Session, driver_id: str, vehicle_id: str) -> bool:
    from app.repositories.vehicle_repo import VehicleRepository
    vehicle = VehicleRepository(db).get(vehicle_id)
    if not vehicle:
        return False
    vehicle.driver_id = driver_id
    db.flush()
    return True


def create_driver(db: Session, payload: DriverCreate, admin: User) -> Driver:
    if payload.depot_id:
        get_depot_or_404(db, payload.depot_id)
    driver = Driver(
        id=generate_ulid(),
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        license_number=payload.license_number,
        license_expiry=payload.license_expiry,
        status=payload.status.value,
        depot_id=payload.depot_id,
        admin_id=admin.id,
    )
    repo = DriverRepository(db)
    repo.create(driver)
    if payload.vehicle_id:
        _assign_vehicle(db, driver.id, payload.vehicle_id)
        db.commit()
        db.refresh(driver)
    return driver


def get_driver_or_404(db: Session, driver_id: str) -> Driver:
    driver = DriverRepository(db).get(driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return driver


def list_drivers(db: Session, depot_id: str | None = None) -> list[Driver]:
    repo = DriverRepository(db)
    if depot_id:
        return repo.list_by_depot(depot_id)
    return repo.list()


def update_driver(db: Session, driver_id: str, payload: DriverUpdate) -> Driver:
    driver = get_driver_or_404(db, driver_id)
    updates = payload.model_dump(exclude_none=True)
    vehicle_id = updates.pop("vehicle_id", None)
    if "depot_id" in updates:
        get_depot_or_404(db, updates["depot_id"])
    if "status" in updates:
        updates["status"] = updates["status"].value
    updated = DriverRepository(db).update(driver, **updates)
    if vehicle_id:
        _assign_vehicle(db, driver_id, vehicle_id)
        db.commit()
        db.refresh(updated)
    return updated


def delete_driver(db: Session, driver_id: str) -> None:
    driver = get_driver_or_404(db, driver_id)
    if driver.vehicles:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete driver '{driver_id}': assigned to {len(driver.vehicles)} vehicle(s)",
        )
    DriverRepository(db).delete(driver)
