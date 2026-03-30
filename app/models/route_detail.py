from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, Text

from app.database.connection import Base


class RouteDetail(Base):
    __tablename__ = "route_details"

    route_id = Column(String, primary_key=True)
    vehicle_id = Column(String, nullable=False)
    status = Column(String, nullable=False, default="planned")
    stops = Column(JSON, nullable=False, default=list)
    total_distance_km = Column(Float, nullable=False, default=0.0)
    total_duration_minutes = Column(Float, nullable=False, default=0.0)
    stop_count = Column(Integer, nullable=False, default=0)
    completed_stops = Column(Integer, nullable=False, default=0)
    status_note = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
