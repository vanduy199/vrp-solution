from sqlalchemy import Column, String, Float, Integer
from app.database.connection import Base


class Vehicle(Base):
    __tablename__ = "vehicles"
    vehicle_id = Column(String, primary_key=True)
    license_plate = Column(String)
    capacity = Column(Integer)
    cost_per_km = Column(Float)
    cost_per_hour = Column(Float)
    max_shift_hours = Column(Integer)
    depot_lat = Column(Float)
    depot_lon = Column(Float)
    driver_name = Column(String)
    status = Column(String, default="active")