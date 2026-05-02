from __future__ import annotations

from datetime import datetime, time

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import Coordinates, ORMModel


def _flat_to_coordinates(data: dict) -> dict:
    """Convert flat lat/lng to nested coordinates if needed."""
    if isinstance(data, dict) and "coordinates" not in data:
        lat = data.pop("lat", None)
        lng = data.pop("lng", None)
        if lat is not None and lng is not None:
            data["coordinates"] = {"lat": lat, "lng": lng}
    return data


class LocationCreate(BaseModel):
    id: str | None = None
    name: str = Field(..., min_length=1)
    address: str | None = None
    address_string: str | None = None
    coordinates: Coordinates
    demand_kg: int = Field(0, ge=0)
    priority: int = 0
    phone: str | None = None
    time_window_start: time | None = None
    time_window_end: time | None = None
    service_time_mins: int = Field(0, ge=0)

    @model_validator(mode="before")
    @classmethod
    def accept_flat_coords(cls, data):
        return _flat_to_coordinates(data)


class LocationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    address: str | None = None
    address_string: str | None = None
    coordinates: Coordinates | None = None
    demand_kg: int | None = Field(None, ge=0)
    priority: int | None = None
    phone: str | None = None
    time_window_start: time | None = None
    time_window_end: time | None = None
    service_time_mins: int | None = Field(None, ge=0)

    @model_validator(mode="before")
    @classmethod
    def accept_flat_coords(cls, data):
        return _flat_to_coordinates(data)


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
