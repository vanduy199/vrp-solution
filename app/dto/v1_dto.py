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


class VehicleUpdateDTO(BaseModel):
    name: str | None = None
    status: str | None = None
    capacity_kg: int | None = None
    volume_m3: float | None = None
    cost_per_km: float | None = None
    ev: bool | None = None
    license_plate: str | None = None
    cost_per_hour: float | None = None
    max_shift_hours: int | None = None
    depot_lat: float | None = None
    depot_lon: float | None = None
    driver_name: str | None = None


class LocationCreateDTO(BaseModel):
    id: str | None = None
    name: str
    address_string: str = ""
    lat: float
    lng: float
    demand_kg: int = 0
    priority: int = 0
    phone: str = ""
    time_window_start: str = ""
    time_window_end: str = ""
    service_time_mins: int = 0


class LocationUpdateDTO(BaseModel):
    name: str | None = None
    address_string: str | None = None
    lat: float | None = None
    lng: float | None = None
    demand_kg: int | None = None
    priority: int | None = None
    phone: str | None = None
    time_window_start: str | None = None
    time_window_end: str | None = None
    service_time_mins: int | None = None


class UserUpdateDTO(BaseModel):
    full_name: str | None = None
    role: str | None = None
    phone: str | None = None
    email: str | None = None


class DepotUpdateDTO(BaseModel):
    name: str | None = None
    coordinates: DepotCoordinatesDTO | None = None
    operating_windows: list[str] | None = None


class RouteStatusUpdateDTO(BaseModel):
    status: str
    note: str | None = None
