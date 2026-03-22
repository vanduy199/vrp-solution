from sqlalchemy.orm import Session

from app.models.point import Point
from app.repositories.point_repository import create_point as repo_create_point, update_point as repo_update_point, delete_point as repo_delete_point
from app.repositories.point_repository import get_all_points


def list_points(db: Session):
    return get_all_points(db)


def create_point(db: Session, payload: dict):
    point = Point(**payload)
    return repo_create_point(db, point)

def update_point(db: Session, point_id: str, payload: dict):
    point = repo_update_point(db, point_id, payload)
    return point

def delete_point(db: Session, point_id: str):
    point = repo_delete_point(db, point_id)
    return point