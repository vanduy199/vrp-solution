from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.ids import generate_id
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate, UserUpdate


def create_user(db: Session, payload: UserCreate) -> User:
    repo = UserRepository(db)
    if payload.email:
        if repo.get_by_email(payload.email):
            raise HTTPException(status_code=409, detail="Email already registered")
    user_id = payload.id or generate_id("user")
    if repo.get(user_id):
        raise HTTPException(status_code=409, detail="User id already exists")
    user = User(
        id=user_id,
        full_name=payload.full_name,
        role=payload.role.value,
        email=payload.email,
        phone=payload.phone,
    )
    return repo.create(user)


def get_user_or_404(db: Session, user_id: str) -> User:
    user = UserRepository(db).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def list_users(db: Session) -> list[User]:
    return UserRepository(db).list()


def update_user(db: Session, user_id: str, payload: UserUpdate) -> User:
    user = get_user_or_404(db, user_id)
    repo = UserRepository(db)
    updates = payload.model_dump(exclude_none=True)
    if "role" in updates:
        updates["role"] = updates["role"].value
    if "email" in updates and updates["email"] != user.email:
        if repo.get_by_email(updates["email"]):
            raise HTTPException(status_code=409, detail="Email already registered")
    return repo.update(user, **updates)


def delete_user(db: Session, user_id: str) -> None:
    user = get_user_or_404(db, user_id)
    UserRepository(db).delete(user)
