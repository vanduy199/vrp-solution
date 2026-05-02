from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import RouteStatus, StopStatus, TrackingStatus
from app.schemas.common import Coordinates, ORMModel


class RouteStopResponse(ORMModel):
    id: str
    location_id: str
    location_name: str | None = None
    sequence_index: int
    status: StopStatus
    planned_eta: datetime | None = None
    actual_arrived_at: datetime | None = None
    actual_completed_at: datetime | None = None
    proof_of_delivery_url: str | None = None
    notes: str | None = None
    coordinates: Coordinates | None = None

    @classmethod
    def from_model(cls, stop) -> "RouteStopResponse":
        return cls(
            id=stop.id,
            location_id=stop.location_id,
            location_name=stop.location.name if stop.location else None,
            sequence_index=stop.sequence_index,
            status=StopStatus(stop.status),
            planned_eta=stop.planned_eta,
            actual_arrived_at=stop.actual_arrived_at,
            actual_completed_at=stop.actual_completed_at,
            proof_of_delivery_url=stop.proof_of_delivery_url,
            notes=stop.notes,
            coordinates=(
                Coordinates(lat=stop.location.lat, lng=stop.location.lng)
                if stop.location
                else None
            ),
        )


class RouteSummary(ORMModel):
    id: str
    vehicle_id: str
    depot_id: str
    job_id: str | None = None
    status: RouteStatus
    total_distance_km: float
    total_duration_mins: float
    total_cost: float
    load_kg: int
    utilization_pct: float
    stop_count: int


class RouteDetail(RouteSummary):
    status_note: str | None = None
    stops: list[RouteStopResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    dispatched_at: datetime | None = None
    completed_at: datetime | None = None


class RouteStatusUpdate(BaseModel):
    status: RouteStatus
    note: str | None = None


class RouteAdjust(BaseModel):
    stop_id: str
    source_route_id: str
    target_route_id: str
    new_sequence_index: int = Field(..., ge=0)


class ActiveRouteResponse(ORMModel):
    route_id: str
    vehicle_id: str
    driver_name: str | None = None
    tracking_status: TrackingStatus
    progress_percentage: float
    current_coordinates: Coordinates
    next_stop: RouteStopResponse | None = None
    delay_mins: int
    updated_at: datetime
