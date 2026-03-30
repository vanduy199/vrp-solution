from sqlalchemy.orm import Session

from app.models.active_route import ActiveRoute


def create_active_route(db: Session, active_route: ActiveRoute) -> ActiveRoute:
    db.add(active_route)
    db.commit()
    db.refresh(active_route)
    return active_route


def get_all_active_routes(db: Session) -> list[ActiveRoute]:
    return db.query(ActiveRoute).filter(ActiveRoute.status.in_(["on-time", "delayed"])).all()


def get_active_route_by_id(db: Session, route_id: str) -> ActiveRoute | None:
    return db.query(ActiveRoute).filter(ActiveRoute.route_id == route_id).first()


def update_active_route(db: Session, route_id: str, updates: dict) -> ActiveRoute | None:
    route = get_active_route_by_id(db, route_id)
    if not route:
        return None
    
    for key, value in updates.items():
        if hasattr(route, key):
            setattr(route, key, value)
    
    db.commit()
    db.refresh(route)
    return route


def delete_active_route(db: Session, route_id: str) -> ActiveRoute | None:
    route = get_active_route_by_id(db, route_id)
    if route:
        db.delete(route)
        db.commit()
    return route
