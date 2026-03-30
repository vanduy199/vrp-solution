from sqlalchemy.orm import Session

from app.models.driver_stop import DriverStop


def create_driver_stop(db: Session, driver_stop: DriverStop) -> DriverStop:
    db.add(driver_stop)
    db.commit()
    db.refresh(driver_stop)
    return driver_stop


def get_all_driver_stops(db: Session) -> list[DriverStop]:
    return db.query(DriverStop).all()


def get_driver_stop_by_id(db: Session, stop_id: str) -> DriverStop | None:
    return db.query(DriverStop).filter(DriverStop.stop_id == stop_id).first()


def update_driver_stop(db: Session, stop_id: str, updates: dict) -> DriverStop | None:
    stop = get_driver_stop_by_id(db, stop_id)
    if not stop:
        return None
    
    for key, value in updates.items():
        if hasattr(stop, key):
            setattr(stop, key, value)
    
    db.commit()
    db.refresh(stop)
    return stop


def delete_driver_stop(db: Session, stop_id: str) -> DriverStop | None:
    stop = get_driver_stop_by_id(db, stop_id)
    if stop:
        db.delete(stop)
        db.commit()
    return stop
