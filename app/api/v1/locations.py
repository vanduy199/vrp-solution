from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import SuccessResponse
from app.schemas.location import LocationCreate, LocationResponse, LocationUpdate
from app.services.location_service import (
    create_location,
    delete_location,
    get_location_or_404,
    list_locations,
    update_location,
    upload_manifest,
)

router = APIRouter(prefix="/locations")


@router.get("/demand", response_model=list[LocationResponse])
def get_demand_locations(db: Session = Depends(get_db)):
    return [LocationResponse.from_model(loc) for loc in list_locations(db)]


@router.post("", response_model=LocationResponse, status_code=201)
def create_location_endpoint(payload: LocationCreate, db: Session = Depends(get_db)):
    return LocationResponse.from_model(create_location(db, payload))


@router.get("/{location_id}", response_model=LocationResponse)
def get_location(location_id: str, db: Session = Depends(get_db)):
    return LocationResponse.from_model(get_location_or_404(db, location_id))


@router.put("/{location_id}", response_model=LocationResponse)
def update_location_endpoint(location_id: str, payload: LocationUpdate, db: Session = Depends(get_db)):
    return LocationResponse.from_model(update_location(db, location_id, payload))


@router.delete("/{location_id}", status_code=204)
def delete_location_endpoint(location_id: str, db: Session = Depends(get_db)):
    delete_location(db, location_id)


@router.post("/upload-manifest")
async def upload_manifest_endpoint(file: UploadFile = File(...), db: Session = Depends(get_db)):
    result = await upload_manifest(db, file)
    return {"success": True, "message": "Manifest processed", **result}
