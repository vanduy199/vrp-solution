"""
Depot-scoped access helpers.
Every query that returns user-facing data must be filtered through these.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_depot import UserDepot


def get_user_depot_ids(db: Session, user: User) -> list[str]:
    """Return depot IDs the current user is allowed to access."""
    rows = db.query(UserDepot.depot_id).filter(UserDepot.user_id == user.id).all()
    return [r.depot_id for r in rows]


def assert_depot_access(db: Session, user: User, depot_id: str) -> None:
    """Raise 403 if the user is not assigned to the given depot."""
    allowed = get_user_depot_ids(db, user)
    if depot_id not in allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: you are not assigned to depot '{depot_id}'",
        )
