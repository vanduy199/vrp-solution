from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
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
def get_vehicles(db: Session = Depends(get_db)):
    return [VehicleResponse.from_model(v) for v in list_vehicles(db)]


@router.post("/vehicles", response_model=VehicleResponse, status_code=201)
def create_vehicle_endpoint(payload: VehicleCreate, db: Session = Depends(get_db)):
    return VehicleResponse.from_model(create_vehicle(db, payload))


@router.get("/vehicles/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(vehicle_id: str, db: Session = Depends(get_db)):
    return VehicleResponse.from_model(get_vehicle_or_404(db, vehicle_id))


@router.put("/vehicles/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle_endpoint(vehicle_id: str, payload: VehicleUpdate, db: Session = Depends(get_db)):
    return VehicleResponse.from_model(update_vehicle(db, vehicle_id, payload))


@router.delete("/vehicles/{vehicle_id}", status_code=204)
def delete_vehicle_endpoint(vehicle_id: str, db: Session = Depends(get_db)):
    delete_vehicle(db, vehicle_id)
