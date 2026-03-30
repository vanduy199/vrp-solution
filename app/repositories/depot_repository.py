from sqlalchemy.orm import Session

from app.models.depot import Depot


def create_depot(db: Session, depot: Depot) -> Depot:
    db.add(depot)
    db.commit()
    db.refresh(depot)
    return depot


def get_all_depots(db: Session) -> list[Depot]:
    return db.query(Depot).all()


def get_depot_by_id(db: Session, depot_id: str) -> Depot | None:
    return db.query(Depot).filter(Depot.id == depot_id).first()


def update_depot(db: Session, depot_id: str, updates: dict) -> Depot | None:
    depot = get_depot_by_id(db, depot_id)
    if not depot:
        return None
    
    for key, value in updates.items():
        if hasattr(depot, key):
            setattr(depot, key, value)
    
    db.commit()
    db.refresh(depot)
    return depot


def delete_depot(db: Session, depot_id: str) -> Depot | None:
    depot = get_depot_by_id(db, depot_id)
    if depot:
        db.delete(depot)
        db.commit()
    return depot
