from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services.auth_service import change_password, login, register

router = APIRouter(prefix="/auth", tags=["Auth"])


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/login", response_model=TokenResponse)
def login_endpoint(payload: LoginRequest, db: Session = Depends(get_db)):
    return login(db, payload)


@router.post("/login/form", response_model=TokenResponse, include_in_schema=False)
def login_form(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return login(db, LoginRequest(email=form.username, password=form.password))


@router.post("/register", response_model=TokenResponse, status_code=201)
def register_endpoint(payload: RegisterRequest, db: Session = Depends(get_db)):
    return register(db, payload)


@router.post("/change-password", status_code=204)
def change_password_endpoint(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    change_password(db, current_user.id, payload.old_password, payload.new_password)


@router.get("/me", response_model=None)
def me(current_user: User = Depends(get_current_user)):
    from app.schemas.user import UserResponse
    return UserResponse.model_validate(current_user)
