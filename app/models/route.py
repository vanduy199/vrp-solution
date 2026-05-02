from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.enums import RouteStatus
from app.models.base import TimestampMixin


class Route(Base, TimestampMixin):
    __tablename__ = "routes"

    id = Column(String, primary_key=True)
    job_id = Column(String, ForeignKey("optimization_jobs.id", ondelete="SET NULL"))
    vehicle_id = Column(String, ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False)
    depot_id = Column(String, ForeignKey("depots.id", ondelete="RESTRICT"), nullable=False)

    status = Column(String, nullable=False, default=RouteStatus.PLANNED.value, index=True)
    status_note = Column(Text)

    total_distance_km = Column(Float, nullable=False, default=0.0)
    total_duration_mins = Column(Float, nullable=False, default=0.0)
    total_cost = Column(Float, nullable=False, default=0.0)
    load_kg = Column(Integer, nullable=False, default=0)
    utilization_pct = Column(Float, nullable=False, default=0.0)

    dispatched_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    job = relationship("OptimizationJob", back_populates="routes")
    vehicle = relationship("Vehicle", back_populates="routes")
    depot = relationship("Depot", back_populates="routes")
    stops = relationship(
        "RouteStop",
        back_populates="route",
        cascade="all, delete-orphan",
        order_by="RouteStop.sequence_index",
    )
    active = relationship(
        "ActiveRoute",
        back_populates="route",
        uselist=False,
        cascade="all, delete-orphan",
    )
