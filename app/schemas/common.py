from datetime import time
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Coordinates(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class TimeWindow(BaseModel):
    start: time
    end: time


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = 1
    page_size: int = 20


class SuccessResponse(BaseModel):
    success: bool = True
    message: str | None = None
