from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import VehicleStatus
from app.schemas.common import ORMModel


class VehicleCreate(BaseModel):
    id: str | None = None
    name: str = Field(..., min_length=1)
    license_plate: str | None = None
    status: VehicleStatus = VehicleStatus.AVAILABLE
    capacity_kg: int = Field(0, ge=0)
    volume_m3: float = Field(0.0, ge=0)
    cost_per_km: float = Field(0.0, ge=0)
    cost_per_hour: float | None = Field(None, ge=0)
    max_shift_hours: int | None = Field(None, ge=0)
    ev: bool = False
    depot_id: str
    driver_id: str | None = None


class VehicleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    license_plate: str | None = None
    status: VehicleStatus | None = None
    capacity_kg: int | None = Field(None, ge=0)
    volume_m3: float | None = Field(None, ge=0)
    cost_per_km: float | None = Field(None, ge=0)
    cost_per_hour: float | None = Field(None, ge=0)
    max_shift_hours: int | None = Field(None, ge=0)
    ev: bool | None = None
    depot_id: str | None = None
    driver_id: str | None = None


class VehicleResponse(ORMModel):
    id: str
    name: str
    license_plate: str | None = None
    status: VehicleStatus
    capacity_kg: int
    volume_m3: float
    cost_per_km: float
    cost_per_hour: float | None = None
    max_shift_hours: int | None = None
    ev: bool
    depot_id: str
    driver_id: str | None = None
    driver_name: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, vehicle) -> "VehicleResponse":
        return cls(
            id=vehicle.id,
            name=vehicle.name,
            license_plate=vehicle.license_plate,
            status=VehicleStatus(vehicle.status),
            capacity_kg=vehicle.capacity_kg,
            volume_m3=vehicle.volume_m3,
            cost_per_km=vehicle.cost_per_km,
            cost_per_hour=vehicle.cost_per_hour,
            max_shift_hours=vehicle.max_shift_hours,
            ev=vehicle.ev,
            depot_id=vehicle.depot_id,
            driver_id=vehicle.driver_id,
            driver_name=vehicle.driver.full_name if vehicle.driver else None,
            created_at=vehicle.created_at,
            updated_at=vehicle.updated_at,
        )
