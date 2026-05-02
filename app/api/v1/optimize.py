from datetime import datetime, timezone
from typing import Any, cast
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import JobStatus, SolverAlgorithm, Objective
from app.schemas.optimization import JobDetail, JobSummary, OptimizeRunRequest, OptimizeRunResponse
from app.services.kafka_service import publish_test_event
from app.services.optimization_service import (
    cancel_job,
    create_job,
    get_job_or_404,
    list_jobs,
    materialize_job,
)

router = APIRouter(prefix="/optimize")


def _job_summary(job) -> JobSummary:
    return JobSummary(
        job_id=job.id,
        project_id=job.project_id,
        status=JobStatus(job.status),
        solver_algorithm=SolverAlgorithm(job.solver_algorithm),
        objective=Objective(job.objective),
        estimated_time_seconds=job.estimated_time_seconds,
        created_at=job.created_at,
    )


def _job_detail(job) -> JobDetail:
    return JobDetail(
        job_id=job.id,
        project_id=job.project_id,
        status=JobStatus(job.status),
        solver_algorithm=SolverAlgorithm(job.solver_algorithm),
        objective=Objective(job.objective),
        estimated_time_seconds=job.estimated_time_seconds,
        created_at=job.created_at,
        vehicle_ids=list(job.vehicle_ids or []),
        location_ids=list(job.location_ids or []),
        constraints=dict(job.constraints or {}),
        result=job.result,
        ready_at=job.ready_at,
        completed_at=job.completed_at,
    )


@router.post("/run", response_model=OptimizeRunResponse, status_code=202)
def run_optimizer(payload: OptimizeRunRequest, db: Session = Depends(get_db)):
    job = create_job(db, payload)
    return OptimizeRunResponse(
        job_id=cast(str, job.id),
        status=JobStatus(job.status),
        estimated_time_seconds=cast(float, job.estimated_time_seconds),
    )


@router.get("/jobs", response_model=list[JobSummary])
def get_jobs(db: Session = Depends(get_db)):
    jobs = list_jobs(db)
    for job in jobs:
        materialize_job(db, job)
    return [_job_summary(j) for j in jobs]


@router.get("/job/{job_id}", response_model=JobDetail)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = get_job_or_404(db, job_id)
    materialize_job(db, job)
    db.refresh(job)
    return _job_detail(job)


@router.get("/job/{job_id}/result")
def get_job_result(job_id: str, db: Session = Depends(get_db)):
    job = get_job_or_404(db, job_id)
    materialize_job(db, job)
    db.refresh(job)
    if job.status != JobStatus.COMPLETED.value:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="Job result is not available yet")
    return job.result


@router.post("/job/{job_id}/cancel", response_model=JobSummary)
def cancel_job_endpoint(job_id: str, db: Session = Depends(get_db)):
    job = cancel_job(db, job_id)
    return _job_summary(job)


@router.get("/test")
def test_endpoint(background_tasks: BackgroundTasks):
    event_id = str(uuid4())
    background_tasks.add_task(
        publish_test_event,
        {
            "event_id": event_id,
            "event_type": "API_TEST_CALLED",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {"success": True, "event_id": event_id}
