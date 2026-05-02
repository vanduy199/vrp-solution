from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.enums import StopStatus
from app.models.base import TimestampMixin


class RouteStop(Base, TimestampMixin):
    __tablename__ = "route_stops"
    __table_args__ = (
        UniqueConstraint("route_id", "sequence_index", name="uq_route_stops_seq"),
    )

    id = Column(String, primary_key=True)
    route_id = Column(
        String, ForeignKey("routes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location_id = Column(String, ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False)
    sequence_index = Column(Integer, nullable=False)

    status = Column(String, nullable=False, default=StopStatus.PENDING.value, index=True)
    planned_eta = Column(DateTime(timezone=True))
    actual_arrived_at = Column(DateTime(timezone=True))
    actual_completed_at = Column(DateTime(timezone=True))
    proof_of_delivery_url = Column(String)
    notes = Column(Text)

    route = relationship("Route", back_populates="stops")
    location = relationship("Location", back_populates="stops")
