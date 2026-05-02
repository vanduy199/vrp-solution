from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.enums import VehicleStatus
from app.models.base import TimestampMixin


class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    license_plate = Column(String)
    status = Column(String, nullable=False, default=VehicleStatus.AVAILABLE.value)

    capacity_kg = Column(Integer, nullable=False, default=0)
    volume_m3 = Column(Float, nullable=False, default=0.0)
    cost_per_km = Column(Float, nullable=False, default=0.0)
    cost_per_hour = Column(Float)
    max_shift_hours = Column(Integer)
    ev = Column(Boolean, nullable=False, default=False)

    depot_id = Column(String, ForeignKey("depots.id", ondelete="RESTRICT"), nullable=False)
    driver_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"))

    depot = relationship("Depot", back_populates="vehicles")
    driver = relationship("User", back_populates="vehicles")
    routes = relationship("Route", back_populates="vehicle")
