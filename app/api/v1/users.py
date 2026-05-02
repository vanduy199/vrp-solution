from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import (
    create_user,
    delete_user,
    get_user_or_404,
    list_users,
    update_user,
)

router = APIRouter(prefix="/users")


@router.get("", response_model=list[UserResponse])
def get_users(db: Session = Depends(get_db)):
    return list_users(db)


@router.post("", response_model=UserResponse, status_code=201)
def create_user_endpoint(payload: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, payload)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db)):
    return get_user_or_404(db, user_id)


@router.put("/{user_id}", response_model=UserResponse)
def update_user_endpoint(user_id: str, payload: UserUpdate, db: Session = Depends(get_db)):
    return update_user(db, user_id, payload)


@router.delete("/{user_id}", status_code=204)
def delete_user_endpoint(user_id: str, db: Session = Depends(get_db)):
    delete_user(db, user_id)
