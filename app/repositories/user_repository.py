from sqlalchemy.orm import Session

from app.models.user import User


def create_user(db: Session, user: User) -> User:
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_all_users(db: Session) -> list[User]:
    return db.query(User).all()


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def update_user(db: Session, user_id: str, updates: dict) -> User | None:
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    
    for key, value in updates.items():
        if hasattr(user, key):
            setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: str) -> User | None:
    user = get_user_by_id(db, user_id)
    if user:
        db.delete(user)
        db.commit()
    return user
