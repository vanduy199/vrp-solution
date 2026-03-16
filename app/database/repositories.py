from sqlalchemy.orm import Session
from app.models.point import Point


def create_point(db: Session, point):

    db.add(point)
    db.commit()
    db.refresh(point)

    return point


def get_points(db: Session):

    return db.query(Point).all()


def get_point(db: Session, point_id):

    return db.query(Point).filter(Point.id == point_id).first()


def delete_point(db: Session, point_id):

    point = db.query(Point).filter(Point.id == point_id).first()

    if point:
        db.delete(point)
        db.commit()

    return point