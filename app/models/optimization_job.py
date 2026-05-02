from sqlalchemy import JSON, Column, DateTime, Float, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.enums import JobStatus
from app.models.base import TimestampMixin


class OptimizationJob(Base, TimestampMixin):
    __tablename__ = "optimization_jobs"

    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False, index=True)
    solver_algorithm = Column(String, nullable=False)
    objective = Column(String, nullable=False)
    status = Column(String, nullable=False, default=JobStatus.PENDING.value, index=True)

    vehicle_ids = Column(JSON, nullable=False, default=list)
    location_ids = Column(JSON, nullable=False, default=list)
    constraints = Column(JSON, nullable=False, default=dict)

    estimated_time_seconds = Column(Float, nullable=False, default=0.0)
    ready_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    result = Column(JSON)

    routes = relationship("Route", back_populates="job")
