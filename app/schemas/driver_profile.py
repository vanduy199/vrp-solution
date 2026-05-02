from __future__ import annotations

from datetime import date

from pydantic import BaseModel, field_validator

from app.core.enums import DriverStatus


def _empty_to_none(v: str | None) -> str | None:
    if v is not None and isinstance(v, str) and v.strip() == "":
        return None
    return v


class DriverCreate(BaseModel):
    full_name: str
    email: str | None = None
    phone: str | None = None
    license_number: str | None = None
    license_expiry: date | None = None
    depot_id: str | None = None
    vehicle_id: str | None = None
    status: DriverStatus = DriverStatus.ACTIVE

    @field_validator("depot_id", "email", "phone", "license_number", "vehicle_id", mode="before")
    @classmethod
    def empty_to_none(cls, v):
        return _empty_to_none(v)


class DriverUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    license_number: str | None = None
    license_expiry: date | None = None
    depot_id: str | None = None
    vehicle_id: str | None = None
    status: DriverStatus | None = None

    @field_validator("depot_id", "email", "phone", "license_number", "vehicle_id", mode="before")
    @classmethod
    def empty_to_none(cls, v):
        return _empty_to_none(v)


class DriverResponse(BaseModel):
    id: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    license_number: str | None = None
    license_expiry: date | None = None
    status: DriverStatus
    depot_id: str | None = None
    admin_id: str | None = None
    vehicle_id: str | None = None
    vehicle_name: str | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, driver) -> "DriverResponse":
        vehicle = driver.vehicles[0] if driver.vehicles else None
        return cls(
            id=driver.id,
            full_name=driver.full_name,
            email=driver.email,
            phone=driver.phone,
            license_number=driver.license_number,
            license_expiry=driver.license_expiry,
            status=DriverStatus(driver.status),
            depot_id=driver.depot_id,
            admin_id=driver.admin_id,
            vehicle_id=vehicle.id if vehicle else None,
            vehicle_name=vehicle.name if vehicle else None,
        )
