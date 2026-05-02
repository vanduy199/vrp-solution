from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.enums import JobStatus, Objective, SolverAlgorithm
from app.schemas.common import ORMModel


class OptimizeRunRequest(BaseModel):
    project_id: str
    solver_algorithm: SolverAlgorithm = SolverAlgorithm.NEAREST_NEIGHBOR
    objective: Objective = Objective.MINIMIZE_DISTANCE
    vehicles: list[str] = Field(..., min_length=1)
    locations: list[str] = Field(..., min_length=1)
    constraints: dict[str, Any] = Field(default_factory=dict)


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
