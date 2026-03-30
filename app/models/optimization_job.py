from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, JSON, String

from app.database.connection import Base


class OptimizationJob(Base):
    __tablename__ = "optimization_jobs"

    job_id = Column(String, primary_key=True)
    status = Column(String, nullable=False)
    project_id = Column(String, nullable=False)
    solver_algorithm = Column(String, nullable=False)
    objective = Column(String, nullable=False)
    vehicle_ids = Column(JSON, nullable=False, default=list)
    location_ids = Column(JSON, nullable=False, default=list)
    constraints = Column(JSON, nullable=False, default=dict)
    estimated_time_seconds = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    ready_at = Column(DateTime(timezone=True), nullable=False)
    result = Column(JSON)
