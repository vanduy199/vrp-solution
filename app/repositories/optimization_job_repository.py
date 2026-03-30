from sqlalchemy.orm import Session

from app.models.optimization_job import OptimizationJob


def create_optimization_job(db: Session, job: OptimizationJob) -> OptimizationJob:
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_all_optimization_jobs(db: Session) -> list[OptimizationJob]:
    return db.query(OptimizationJob).all()


def get_optimization_job_by_id(db: Session, job_id: str) -> OptimizationJob | None:
    return db.query(OptimizationJob).filter(OptimizationJob.job_id == job_id).first()


def update_optimization_job(db: Session, job_id: str, updates: dict) -> OptimizationJob | None:
    job = get_optimization_job_by_id(db, job_id)
    if not job:
        return None
    
    for key, value in updates.items():
        if hasattr(job, key):
            setattr(job, key, value)
    
    db.commit()
    db.refresh(job)
    return job


def delete_optimization_job(db: Session, job_id: str) -> OptimizationJob | None:
    job = get_optimization_job_by_id(db, job_id)
    if job:
        db.delete(job)
        db.commit()
    return job
