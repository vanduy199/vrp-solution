from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.ids import generate_id
from app.models.depot import Depot
from app.repositories.depot_repo import DepotRepository
from app.schemas.depot import DepotCreate, DepotUpdate


def create_depot(db: Session, payload: DepotCreate) -> Depot:
    repo = DepotRepository(db)
    depot_id = payload.id or generate_id("depot")
    if repo.get(depot_id):
        raise HTTPException(status_code=409, detail="Depot id already exists")
    depot = Depot(
        id=depot_id,
        name=payload.name,
        lat=payload.coordinates.lat,
        lng=payload.coordinates.lng,
        address=payload.address,
        operating_windows=payload.operating_windows,
    )
    return repo.create(depot)


def get_depot_or_404(db: Session, depot_id: str) -> Depot:
    depot = DepotRepository(db).get(depot_id)
    if not depot:
        raise HTTPException(status_code=404, detail="Depot not found")
    return depot


def list_depots(db: Session) -> list[Depot]:
    return DepotRepository(db).list()


def update_depot(db: Session, depot_id: str, payload: DepotUpdate) -> Depot:
    depot = get_depot_or_404(db, depot_id)
    updates: dict = {}
    if payload.name is not None:
        updates["name"] = payload.name
    if payload.coordinates is not None:
        updates["lat"] = payload.coordinates.lat
        updates["lng"] = payload.coordinates.lng
    if payload.address is not None:
        updates["address"] = payload.address
    if payload.operating_windows is not None:
        updates["operating_windows"] = payload.operating_windows
    return DepotRepository(db).update(depot, **updates)


def delete_depot(db: Session, depot_id: str) -> None:
    depot = get_depot_or_404(db, depot_id)
    if depot.vehicles:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete depot '{depot_id}': it has {len(depot.vehicles)} vehicle(s) assigned",
        )
    DepotRepository(db).delete(depot)
