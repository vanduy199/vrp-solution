from sqlalchemy import Column, Date, ForeignKey, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.enums import DriverStatus
from app.models.base import TimestampMixin


class Driver(Base, TimestampMixin):
    __tablename__ = "drivers"

    id = Column(String, primary_key=True)
    full_name = Column(String, nullable=False)
    email = Column(String)
    phone = Column(String)
    license_number = Column(String)
    license_expiry = Column(Date)
    status = Column(String, nullable=False, default=DriverStatus.ACTIVE.value)

    depot_id = Column(String, ForeignKey("depots.id", ondelete="SET NULL"))
    admin_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"))

    depot = relationship("Depot", back_populates="drivers")
    admin = relationship("User", back_populates="managed_drivers")
    vehicles = relationship("Vehicle", back_populates="driver")
