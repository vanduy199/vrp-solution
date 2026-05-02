from datetime import datetime, time

from pydantic import BaseModel, Field

from app.schemas.common import Coordinates, ORMModel


class LocationCreate(BaseModel):
    id: str | None = None
    name: str = Field(..., min_length=1)
    address: str | None = None
    coordinates: Coordinates
    demand_kg: int = Field(0, ge=0)
    priority: int = 0
    phone: str | None = None
    time_window_start: time | None = None
    time_window_end: time | None = None
    service_time_mins: int = Field(0, ge=0)


class LocationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    address: str | None = None
    coordinates: Coordinates | None = None
    demand_kg: int | None = Field(None, ge=0)
    priority: int | None = None
    phone: str | None = None
    time_window_start: time | None = None
    time_window_end: time | None = None
    service_time_mins: int | None = Field(None, ge=0)


class LocationResponse(ORMModel):
    id: str
    name: str
    address: str | None = None
    coordinates: Coordinates
    demand_kg: int
    priority: int
    phone: str | None = None
    time_window_start: time | None = None
    time_window_end: time | None = None
    service_time_mins: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, location) -> "LocationResponse":
        return cls(
            id=location.id,
            name=location.name,
            address=location.address,
            coordinates=Coordinates(lat=location.lat, lng=location.lng),
            demand_kg=location.demand_kg,
            priority=location.priority,
            phone=location.phone,
            time_window_start=location.time_window_start,
            time_window_end=location.time_window_end,
            service_time_mins=location.service_time_mins,
            created_at=location.created_at,
            updated_at=location.updated_at,
        )
