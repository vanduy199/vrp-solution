from pydantic import BaseModel, EmailStr

from app.schemas.common import ORMModel
from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    phone: str | None = None
