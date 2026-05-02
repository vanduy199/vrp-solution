from sqlalchemy import Column, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class UserDepot(Base, TimestampMixin):
    __tablename__ = "user_depots"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    depot_id = Column(String, ForeignKey("depots.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "depot_id", name="uq_user_depot"),
    )

    user = relationship("User", back_populates="depot_assignments")
    depot = relationship("Depot", back_populates="user_assignments")
