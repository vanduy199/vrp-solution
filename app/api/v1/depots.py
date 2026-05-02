from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.scope import assert_depot_access, get_user_depot_ids
from app.models.user import User
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
def get_depots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    allowed_ids = get_user_depot_ids(db, current_user)
    all_depots = list_depots(db)
    return [DepotResponse.from_model(d) for d in all_depots if d.id in allowed_ids]


@router.post("", response_model=DepotResponse, status_code=201)
def create_depot_endpoint(
    payload: DepotCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    depot = create_depot(db, payload)
    from app.services.user_depot_service import assign_depot
    from app.core.ids import generate_id
    from app.models.user_depot import UserDepot
    ud = UserDepot(id=generate_id("ud"), user_id=current_user.id, depot_id=depot.id)
    db.add(ud)
    db.commit()
    return DepotResponse.from_model(depot)


@router.get("/{depot_id}", response_model=DepotResponse)
def get_depot(
    depot_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assert_depot_access(db, current_user, depot_id)
    return DepotResponse.from_model(get_depot_or_404(db, depot_id))


@router.put("/{depot_id}", response_model=DepotResponse)
def update_depot_endpoint(
    depot_id: str,
    payload: DepotUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assert_depot_access(db, current_user, depot_id)
    return DepotResponse.from_model(update_depot(db, depot_id, payload))


@router.delete("/{depot_id}")
def delete_depot_endpoint(
    depot_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assert_depot_access(db, current_user, depot_id)
    delete_depot(db, depot_id)
    return {"success": True, "message": f"Depot '{depot_id}' deleted"}
