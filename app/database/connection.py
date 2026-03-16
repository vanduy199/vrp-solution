from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.utils.config import settings

# Tạo engine kết nối database
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # dùng cho SQLite
)

# Tạo session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class cho models
Base = declarative_base()


# Dependency dùng cho FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()