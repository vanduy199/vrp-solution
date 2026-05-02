from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

database_url = settings.DATABASE_URL
engine_kwargs: dict = {"echo": settings.DB_ECHO}

if database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
elif database_url.startswith("mysql+pymysql"):
    parsed = make_url(database_url)
    query_params = dict(parsed.query)
    ssl_mode = query_params.pop("ssl_mode", None) or query_params.pop("ssl-mode", None)
    if ssl_mode and str(ssl_mode).upper() in {"REQUIRED", "VERIFY_CA", "VERIFY_IDENTITY"}:
        engine_kwargs["connect_args"] = {"ssl": {}}
    parsed = parsed.set(query=query_params)
    database_url = str(parsed)

engine = create_engine(database_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
