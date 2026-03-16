from sqlalchemy import Column, String, Float, Integer
from app.database.connection import Base


class Point(Base):

    __tablename__ = "points"

    id = Column(String, primary_key=True)

    name = Column(String)

    latitude = Column(Float)
    longitude = Column(Float)

    demand = Column(Integer)

    service_time = Column(Integer)

    priority = Column(Integer)

    phone = Column(String)

    address = Column(String)