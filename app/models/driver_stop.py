from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Text

from app.database.connection import Base


class DriverStop(Base):
    __tablename__ = "driver_stops"

    stop_id = Column(String, primary_key=True)
    status = Column(String, nullable=False)
    proof_of_delivery_url = Column(String)
    notes = Column(Text)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
