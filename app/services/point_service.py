from sqlalchemy.orm import Session

from app.repositories.point_repository import get_all_points, create 


def list_points(db: Session):
    return get_all_points(db)

def create_point(db: Sesssion):
    return 