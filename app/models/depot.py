from sqlalchemy import Column, Float, JSON, String

from app.database.connection import Base


class Depot(Base):
    __tablename__ = "depots"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    operating_windows = Column(JSON, nullable=False, default=list)
