from sqlalchemy import Column, Float, Integer, String, Time
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Location(Base, TimestampMixin):
    __tablename__ = "locations"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    demand_kg = Column(Integer, nullable=False, default=0)
    priority = Column(Integer, nullable=False, default=0)
    phone = Column(String)
    time_window_start = Column(Time)
    time_window_end = Column(Time)
    service_time_mins = Column(Integer, nullable=False, default=0)

    stops = relationship("RouteStop", back_populates="location")
