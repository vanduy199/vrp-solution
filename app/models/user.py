from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    email = Column(String, unique=True)
    phone = Column(String)
    password_hash = Column(String)

    vehicles = relationship("Vehicle", back_populates="driver")
