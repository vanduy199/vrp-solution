from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.enums import JobStatus, Objective, SolverAlgorithm
from app.schemas.common import ORMModel


class VRPConstraints(BaseModel):
    """VRP-specific optimization constraints."""

    max_vehicles: int | None = Field(
        None,
        description="Maximum number of vehicles to use (None = use all available)",
    )
    max_route_distance_km: float | None = Field(
        None,
        description="Maximum distance per route in km",
    )
    max_route_duration_mins: float | None = Field(
        None,
        description="Maximum duration per route in minutes",
    )
    allow_overload: bool = Field(
        False,
        description="Allow slight capacity overloading (penalty-based)",
    )


class OptimizeRunRequest(BaseModel):
    project_id: str
    solver_algorithm: SolverAlgorithm = SolverAlgorithm.NEAREST_NEIGHBOR
    objective: Objective = Objective.MINIMIZE_DISTANCE
    vehicles: list[str] = Field(..., min_length=1)
    locations: list[str] = Field(..., min_length=1)
    constraints: VRPConstraints = Field(default_factory=VRPConstraints)


class OptimizeRunResponse(BaseModel):
    job_id: str
    status: JobStatus
    estimated_time_seconds: float


class JobSummary(ORMModel):
    job_id: str
    project_id: str
    status: JobStatus
    solver_algorithm: SolverAlgorithm
    objective: Objective
    estimated_time_seconds: float
    created_at: datetime


class JobDetail(JobSummary):
    vehicle_ids: list[str]
    location_ids: list[str]
    constraints: dict[str, Any]
    result: dict[str, Any] | None = None
    ready_at: datetime | None = None
    completed_at: datetime | None = None
