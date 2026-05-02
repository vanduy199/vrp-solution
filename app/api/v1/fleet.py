from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.scope import assert_depot_access, get_user_depot_ids
from app.models.user import User
from app.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleUpdate
from app.services.vehicle_service import (
    create_vehicle,
    delete_vehicle,
    get_vehicle_or_404,
    list_vehicles,
    update_vehicle,
)

router = APIRouter(prefix="/fleet")


@router.get("/vehicles", response_model=list[VehicleResponse])
def get_vehicles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    allowed_ids = get_user_depot_ids(db, current_user)
    return [
        VehicleResponse.from_model(v)
        for v in list_vehicles(db)
        if v.depot_id is None or v.depot_id in allowed_ids
    ]


@router.post("/vehicles", response_model=VehicleResponse, status_code=201)
def create_vehicle_endpoint(
    payload: VehicleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.depot_id:
        assert_depot_access(db, current_user, payload.depot_id)
    return VehicleResponse.from_model(create_vehicle(db, payload))


@router.get("/vehicles/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(
    vehicle_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vehicle = get_vehicle_or_404(db, vehicle_id)
    if vehicle.depot_id:
        assert_depot_access(db, current_user, vehicle.depot_id)
    return VehicleResponse.from_model(vehicle)


@router.put("/vehicles/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle_endpoint(
    vehicle_id: str,
    payload: VehicleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vehicle = get_vehicle_or_404(db, vehicle_id)
    if vehicle.depot_id:
        assert_depot_access(db, current_user, vehicle.depot_id)
    if payload.depot_id:
        assert_depot_access(db, current_user, payload.depot_id)
    return VehicleResponse.from_model(update_vehicle(db, vehicle_id, payload))


@router.delete("/vehicles/{vehicle_id}")
def delete_vehicle_endpoint(
    vehicle_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vehicle = get_vehicle_or_404(db, vehicle_id)
    if vehicle.depot_id:
        assert_depot_access(db, current_user, vehicle.depot_id)
    delete_vehicle(db, vehicle_id)
    return {"success": True, "message": f"Vehicle '{vehicle_id}' deleted"}
