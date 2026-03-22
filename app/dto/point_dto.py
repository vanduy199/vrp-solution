from pydantic import BaseModel, ConfigDict


class PointCreateDTO(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    demand: int
    priority: int
    phone: str
    time_window_start: str
    time_window_end: str
    service_time: int
    address: str


class PointResponseDTO(PointCreateDTO):
    model_config = ConfigDict(from_attributes=True)


class PointListResponseDTO(BaseModel):
    count: int
    data: list[PointResponseDTO]

class PointUpdateDTO(BaseModel):
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    demand: int | None = None
    priority: int | None = None
    phone: str | None = None
    time_window_start: str | None = None
    time_window_end: str | None = None
    service_time: int | None = None
    address: str | None = None
