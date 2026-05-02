from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import Coordinates, ORMModel


class DepotCreate(BaseModel):
    id: str | None = None
    name: str = Field(..., min_length=1)
    coordinates: Coordinates
    address: str | None = None
    operating_windows: list[str] = Field(default_factory=list)


class DepotUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    coordinates: Coordinates | None = None
    address: str | None = None
    operating_windows: list[str] | None = None


class DepotResponse(ORMModel):
    id: str
    name: str
    coordinates: Coordinates
    address: str | None = None
    operating_windows: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, depot) -> "DepotResponse":
        return cls(
            id=depot.id,
            name=depot.name,
            coordinates=Coordinates(lat=depot.lat, lng=depot.lng),
            address=depot.address,
            operating_windows=list(depot.operating_windows or []),
            created_at=depot.created_at,
            updated_at=depot.updated_at,
        )
