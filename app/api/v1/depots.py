from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.depot import DepotCreate, DepotResponse, DepotUpdate
from app.services.depot_service import (
    create_depot,
    delete_depot,
    get_depot_or_404,
    list_depots,
    update_depot,
)

router = APIRouter(prefix="/locations/depots")


@router.get("", response_model=list[DepotResponse])
def get_depots(db: Session = Depends(get_db)):
    return [DepotResponse.from_model(d) for d in list_depots(db)]


@router.post("", response_model=DepotResponse, status_code=201)
def create_depot_endpoint(payload: DepotCreate, db: Session = Depends(get_db)):
    return DepotResponse.from_model(create_depot(db, payload))


@router.get("/{depot_id}", response_model=DepotResponse)
def get_depot(depot_id: str, db: Session = Depends(get_db)):
    return DepotResponse.from_model(get_depot_or_404(db, depot_id))


@router.put("/{depot_id}", response_model=DepotResponse)
def update_depot_endpoint(depot_id: str, payload: DepotUpdate, db: Session = Depends(get_db)):
    return DepotResponse.from_model(update_depot(db, depot_id, payload))


@router.delete("/{depot_id}", status_code=204)
def delete_depot_endpoint(depot_id: str, db: Session = Depends(get_db)):
    delete_depot(db, depot_id)
