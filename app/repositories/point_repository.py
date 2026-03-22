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

# Việc get by id trước là không cần thiết, có thể update trực tiếp bằng cách query và update luôn, 
# nhưng để giữ code đơn giản và dễ hiểu thì mình sẽ làm như này
def update_point(db: Session, point_id: str, updated_data: dict):
    point = get_point_by_id(db, point_id)
    if point:
        for key, value in updated_data.items():
            setattr(point, key, value)
        db.commit()
        db.refresh(point)
    return point


