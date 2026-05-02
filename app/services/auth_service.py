from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.ids import generate_id
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse


def login(db: Session, payload: LoginRequest) -> TokenResponse:
    repo = UserRepository(db)
    user = repo.get_by_email(payload.email)
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(subject=user.id, role=user.role)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


def register(db: Session, payload: RegisterRequest) -> TokenResponse:
    repo = UserRepository(db)
    if repo.get_by_email(payload.email):
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        id=generate_id("user"),
        full_name=payload.full_name,
        role=UserRole.DISPATCHER.value,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=user.id, role=user.role)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


def change_password(db: Session, user_id: str, old_password: str, new_password: str) -> None:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.password_hash or not verify_password(old_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    user.password_hash = hash_password(new_password)
    db.commit()
