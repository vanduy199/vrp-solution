from sqlalchemy.orm import Session

from app.models.point import Point


def get_all_points(db: Session):
    return db.query(Point).all()


def get_point_by_id(db: Session, point_id: str):
    return db.query(Point).filter(Point.id == point_id).first()


def create_point(db: Session, point: Point):
    db.add(point)
    db.commit()
    db.refresh(point)
    return point


def delete_point(db: Session, point_id: str):
    point = get_point_by_id(db, point_id)
    if point:
        db.delete(point)
        db.commit()
    return point
