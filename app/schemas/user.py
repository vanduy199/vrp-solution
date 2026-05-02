from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.core.enums import UserRole
from app.schemas.common import ORMModel


class UserCreate(BaseModel):
    id: str | None = None
    full_name: str = Field(..., min_length=1)
    role: UserRole
    email: EmailStr | None = None
    phone: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1)
    role: UserRole | None = None
    email: EmailStr | None = None
    phone: str | None = None


class UserResponse(ORMModel):
    id: str
    full_name: str
    role: UserRole
    email: EmailStr | None = None
    phone: str | None = None
    created_at: datetime
    updated_at: datetime
