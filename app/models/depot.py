from sqlalchemy import JSON, Column, Float, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Depot(Base, TimestampMixin):
    __tablename__ = "depots"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    address = Column(String)
    operating_windows = Column(JSON, nullable=False, default=list)

    vehicles = relationship("Vehicle", back_populates="depot")
    routes = relationship("Route", back_populates="depot")
    drivers = relationship("Driver", back_populates="depot")
    user_assignments = relationship("UserDepot", back_populates="depot", cascade="all, delete-orphan")
