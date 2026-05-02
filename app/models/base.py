from datetime import datetime, timezone

from sqlalchemy import Column, DateTime


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )
