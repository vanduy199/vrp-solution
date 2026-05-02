from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.enums import TrackingStatus
from app.models.base import utcnow


class ActiveRoute(Base):
    __tablename__ = "active_routes"

    route_id = Column(
        String,
        ForeignKey("routes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    progress_percentage = Column(Float, nullable=False, default=0.0)
    current_lat = Column(Float, nullable=False, default=0.0)
    current_lng = Column(Float, nullable=False, default=0.0)
    current_stop_id = Column(
        String,
        ForeignKey("route_stops.id", ondelete="SET NULL", use_alter=True, name="fk_active_current_stop"),
    )
    next_stop_id = Column(
        String,
        ForeignKey("route_stops.id", ondelete="SET NULL", use_alter=True, name="fk_active_next_stop"),
    )
    delay_mins = Column(Integer, nullable=False, default=0)
    tracking_status = Column(String, nullable=False, default=TrackingStatus.ON_TIME.value)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    route = relationship("Route", back_populates="active")
    current_stop = relationship("RouteStop", foreign_keys=[current_stop_id])
    next_stop = relationship("RouteStop", foreign_keys=[next_stop_id])
