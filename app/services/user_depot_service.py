from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.ids import generate_id
from app.models.user_depot import UserDepot
from app.repositories.user_depot_repo import UserDepotRepository
from app.services.depot_service import get_depot_or_404
from app.services.user_service import get_user_or_404


def assign_depot(db: Session, user_id: str, depot_id: str) -> UserDepot:
    get_user_or_404(db, user_id)
    get_depot_or_404(db, depot_id)

    repo = UserDepotRepository(db)
    existing = repo.get_assignment(user_id, depot_id)
    if existing:
        raise HTTPException(status_code=409, detail="User is already assigned to this depot")

    assignment = UserDepot(
        id=generate_id("ud"),
        user_id=user_id,
        depot_id=depot_id,
    )
    return repo.create(assignment)


def unassign_depot(db: Session, user_id: str, depot_id: str) -> None:
    get_user_or_404(db, user_id)
    repo = UserDepotRepository(db)
    assignment = repo.get_assignment(user_id, depot_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    repo.delete(assignment)


def list_depots_for_user(db: Session, user_id: str) -> list[str]:
    get_user_or_404(db, user_id)
    assignments = UserDepotRepository(db).list_by_user(user_id)
    return [a.depot_id for a in assignments]


def list_users_for_depot(db: Session, depot_id: str) -> list[str]:
    get_depot_or_404(db, depot_id)
    assignments = UserDepotRepository(db).list_by_depot(depot_id)
    return [a.user_id for a in assignments]
