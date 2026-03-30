from sqlalchemy.orm import Session

from app.models.route_detail import RouteDetail


def create_route_detail(db: Session, route_detail: RouteDetail) -> RouteDetail:
    db.add(route_detail)
    db.commit()
    db.refresh(route_detail)
    return route_detail


def get_all_route_details(db: Session) -> list[RouteDetail]:
    return db.query(RouteDetail).all()


def get_route_detail_by_id(db: Session, route_id: str) -> RouteDetail | None:
    return db.query(RouteDetail).filter(RouteDetail.route_id == route_id).first()


def update_route_detail(db: Session, route_id: str, updates: dict) -> RouteDetail | None:
    route_detail = get_route_detail_by_id(db, route_id)
    if not route_detail:
        return None
    
    for key, value in updates.items():
        if hasattr(route_detail, key):
            setattr(route_detail, key, value)
    
    db.commit()
    db.refresh(route_detail)
    return route_detail


def delete_route_detail(db: Session, route_id: str) -> RouteDetail | None:
    route_detail = get_route_detail_by_id(db, route_id)
    if route_detail:
        db.delete(route_detail)
        db.commit()
    return route_detail
