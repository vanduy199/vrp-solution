from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.scope import assert_depot_access, get_user_depot_ids
from app.models.user import User
from app.schemas.driver_profile import DriverCreate, DriverResponse, DriverUpdate
from app.services.driver_profile_service import (
    create_driver,
    delete_driver,
    get_driver_or_404,
    list_drivers,
    update_driver,
)

router = APIRouter(prefix="/drivers")


@router.get("", response_model=list[DriverResponse])
def get_drivers(
    depot_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.repositories.driver_repo import DriverRepository
    repo = DriverRepository(db)
    if depot_id:
        assert_depot_access(db, current_user, depot_id)
        drivers = repo.list_by_depot(depot_id)
    else:
        drivers = repo.list_by_admin(current_user.id)
    return [DriverResponse.from_model(d) for d in drivers]


@router.post("", response_model=DriverResponse, status_code=201)
def create_driver_endpoint(
    payload: DriverCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.depot_id:
        assert_depot_access(db, current_user, payload.depot_id)
    return DriverResponse.from_model(create_driver(db, payload, admin=current_user))


@router.get("/{driver_id}", response_model=DriverResponse)
def get_driver(
    driver_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    driver = get_driver_or_404(db, driver_id)
    if driver.depot_id:
        assert_depot_access(db, current_user, driver.depot_id)
    return DriverResponse.from_model(driver)


@router.put("/{driver_id}", response_model=DriverResponse)
def update_driver_endpoint(
    driver_id: str,
    payload: DriverUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    driver = get_driver_or_404(db, driver_id)
    if driver.depot_id:
        assert_depot_access(db, current_user, driver.depot_id)
    if payload.depot_id:
        assert_depot_access(db, current_user, payload.depot_id)
    return DriverResponse.from_model(update_driver(db, driver_id, payload))


@router.delete("/{driver_id}")
def delete_driver_endpoint(
    driver_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    driver = get_driver_or_404(db, driver_id)
    if driver.depot_id:
        assert_depot_access(db, current_user, driver.depot_id)
    delete_driver(db, driver_id)
    return {"success": True, "message": f"Driver '{driver_id}' deleted"}
