from sqlalchemy import Column, String, Float, Integer
from app.database.connection import Base


class Point(Base):
    __tablename__ = "points"
    id = Column(String, primary_key=True)
    name = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    demand = Column(Integer)
    priority = Column(Integer)
    phone = Column(String)
    time_window_start = Column(String)
    time_window_end = Column(String)
    service_time = Column(Integer)
    address = Column(String)