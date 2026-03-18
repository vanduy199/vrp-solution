from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base

from app.utils.config import settings

# Tạo engine kết nối database
database_url = settings.DATABASE_URL

engine_kwargs = {}
if database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
elif database_url.startswith("mysql+pymysql"):
    parsed_url = make_url(database_url)
    query_params = dict(parsed_url.query)
    ssl_mode = query_params.pop("ssl_mode", None) or query_params.pop("ssl-mode", None)

    if ssl_mode and str(ssl_mode).upper() in {"REQUIRED", "VERIFY_CA", "VERIFY_IDENTITY"}:
        engine_kwargs["connect_args"] = {"ssl": {}}

    parsed_url = parsed_url.set(query=query_params)
    database_url = str(parsed_url)

engine = create_engine(database_url, **engine_kwargs)

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