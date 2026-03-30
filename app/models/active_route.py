from sqlalchemy import Column, Float, Integer, String

from app.database.connection import Base


class ActiveRoute(Base):
    __tablename__ = "active_routes"

    route_id = Column(String, primary_key=True)
    vehicle_id = Column(String, nullable=False)
    driver_name = Column(String, nullable=False, default="Unknown")
    status = Column(String, nullable=False, default="on-time")
    progress_percentage = Column(Float, nullable=False, default=0.0)
    current_lat = Column(Float, nullable=False, default=0.0)
    current_lng = Column(Float, nullable=False, default=0.0)
    next_location_id = Column(String)
    next_location_name = Column(String)
    next_eta = Column(String)
    next_stop_index = Column(Integer, nullable=False, default=0)
    total_stops = Column(Integer, nullable=False, default=0)
    delay_mins = Column(Integer, nullable=False, default=0)
