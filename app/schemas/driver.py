from pydantic import BaseModel

from app.core.enums import StopStatus
from app.schemas.route import RouteStopResponse


class DriverStopStatusUpdate(BaseModel):
    status: StopStatus
    proof_of_delivery_url: str | None = None
    notes: str | None = None


class DriverManifestRoute(BaseModel):
    route_id: str
    vehicle_id: str
    driver_name: str | None = None
    stops: list[RouteStopResponse]
