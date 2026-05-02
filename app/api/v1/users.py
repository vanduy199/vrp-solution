from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_depot_service import (
    assign_depot,
    list_depots_for_user,
    unassign_depot,
)
from app.services.user_service import (
    create_user,
    delete_user,
    get_user_or_404,
    list_users,
    update_user,
)

router = APIRouter(prefix="/users")


class DepotAssignBody(BaseModel):
    depot_id: str


@router.get("", response_model=list[UserResponse])
def get_users(db: Session = Depends(get_db)):
    return list_users(db)


@router.post("", response_model=UserResponse, status_code=201)
def create_user_endpoint(payload: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, payload)


@router.get("/me/depots", response_model=list[str])
def get_my_depots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_depots_for_user(db, current_user.id)


@router.post("/me/depots", status_code=201)
def assign_my_depot(
    body: DepotAssignBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assignment = assign_depot(db, current_user.id, body.depot_id)
    return {"user_id": assignment.user_id, "depot_id": assignment.depot_id}


@router.delete("/me/depots/{depot_id}")
def unassign_my_depot(
    depot_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    unassign_depot(db, current_user.id, depot_id)
    return {"success": True, "message": f"Unassigned from depot '{depot_id}'"}


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db)):
    return get_user_or_404(db, user_id)


@router.put("/{user_id}", response_model=UserResponse)
def update_user_endpoint(user_id: str, payload: UserUpdate, db: Session = Depends(get_db)):
    return update_user(db, user_id, payload)


@router.delete("/{user_id}")
def delete_user_endpoint(user_id: str, db: Session = Depends(get_db)):
    delete_user(db, user_id)
    return {"success": True, "message": f"User '{user_id}' deleted"}
