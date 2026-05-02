import io

import pandas as pd
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.ids import generate_id
from app.models.location import Location
from app.repositories.location_repo import LocationRepository
from app.schemas.location import LocationCreate, LocationUpdate


def create_location(db: Session, payload: LocationCreate) -> Location:
    repo = LocationRepository(db)
    loc_id = payload.id or generate_id("loc")
    if repo.get(loc_id):
        raise HTTPException(status_code=409, detail="Location id already exists")
    location = Location(
        id=loc_id,
        name=payload.name,
        address=payload.address or payload.address_string,
        lat=payload.coordinates.lat,
        lng=payload.coordinates.lng,
        demand_kg=payload.demand_kg,
        priority=payload.priority,
        phone=payload.phone,
        time_window_start=payload.time_window_start,
        time_window_end=payload.time_window_end,
        service_time_mins=payload.service_time_mins,
    )
    return repo.create(location)


def get_location_or_404(db: Session, location_id: str) -> Location:
    location = LocationRepository(db).get(location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


def list_locations(db: Session) -> list[Location]:
    return LocationRepository(db).list()


def update_location(db: Session, location_id: str, payload: LocationUpdate) -> Location:
    location = get_location_or_404(db, location_id)
    updates = payload.model_dump(exclude_none=True)
    if "coordinates" in updates:
        coords = updates.pop("coordinates")
        updates["lat"] = coords["lat"]
        updates["lng"] = coords["lng"]
    return LocationRepository(db).update(location, **updates)


def delete_location(db: Session, location_id: str) -> None:
    location = get_location_or_404(db, location_id)
    if LocationRepository(db).is_used_in_route(location_id):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete location '{location_id}': it is used in existing routes",
        )
    LocationRepository(db).delete(location)


def _extract(row: pd.Series, keys: list[str], default=None):
    for k in keys:
        if k in row and pd.notna(row[k]):
            return row[k]
    return default


async def upload_manifest(db: Session, file: UploadFile) -> dict:
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    content = await file.read()

    if ext == "csv":
        df = pd.read_csv(io.BytesIO(content))
    elif ext in {"xlsx", "xls"}:
        df = pd.read_excel(io.BytesIO(content))
    else:
        raise HTTPException(status_code=400, detail="Only .csv, .xlsx, .xls are supported")

    repo = LocationRepository(db)
    created = 0
    skipped = 0
    for _, row in df.iterrows():
        loc_id = str(_extract(row, ["id", "location_id", "stop_id"], generate_id("loc")))
        if repo.get(loc_id):
            skipped += 1
            continue
        location = Location(
            id=loc_id,
            name=str(_extract(row, ["name", "location_name", "customer_name"], "Unknown")),
            address=str(_extract(row, ["address", "address_string"], "") or ""),
            lat=float(_extract(row, ["latitude", "lat"], 0.0) or 0.0),
            lng=float(_extract(row, ["longitude", "lng", "lon"], 0.0) or 0.0),
            demand_kg=int(float(_extract(row, ["demand", "demand_kg", "quantity"], 0) or 0)),
            priority=int(float(_extract(row, ["priority"], 0) or 0)),
            phone=str(_extract(row, ["phone"], "") or ""),
            service_time_mins=int(float(_extract(row, ["service_time", "service_time_mins"], 0) or 0)),
        )
        db.add(location)
        created += 1

    db.commit()
    return {
        "uploaded_rows": int(df.shape[0]),
        "created_locations": created,
        "skipped_existing": skipped,
    }
