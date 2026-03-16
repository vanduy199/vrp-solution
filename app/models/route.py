from sqlalchemy import Column, String, Float
from app.database.connection import Base


class Route(Base):

    __tablename__ = "routes"

    route_id = Column(String, primary_key=True)

    vehicle_id = Column(String)

    total_distance = Column(Float)

    total_duration = Column(Float)

    total_cost = Column(Float)