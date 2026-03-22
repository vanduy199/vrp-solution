from pydantic import BaseModel, Field


class OptimizeRunRequestDTO(BaseModel):
    project_id: str
    solver_algorithm: str
    vehicles: list[str]
    locations: list[str]
    objective: str
    constraints: dict[str, bool] = Field(default_factory=dict)


class DepotCoordinatesDTO(BaseModel):
    lat: float
    lng: float


class DepotCreateDTO(BaseModel):
    name: str
    coordinates: DepotCoordinatesDTO
    operating_windows: list[str] = Field(default_factory=list)


class UserCreateDTO(BaseModel):
    full_name: str
    role: str
    phone: str | None = None
    email: str | None = None


class RouteAdjustDTO(BaseModel):
    stop_id: str
    source_route_id: str
    target_route_id: str
    new_sequence_index: int


class DriverStopStatusUpdateDTO(BaseModel):
    status: str
    proof_of_delivery_url: str | None = None
    notes: str | None = None


class VehicleCreateDTO(BaseModel):
    id: str
    name: str
    status: str = "available"
    capacity_kg: int = 0
    volume_m3: float = 0
    cost_per_km: float = 0
    ev: bool = False
    license_plate: str | None = None
    cost_per_hour: float | None = None
    max_shift_hours: int | None = None
    depot_lat: float | None = None
    depot_lon: float | None = None
    driver_name: str | None = None
