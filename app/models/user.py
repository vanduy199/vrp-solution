from sqlalchemy import Column, String

from app.database.connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    phone = Column(String)
    email = Column(String)
