from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from app.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: Session):
        self.db = db

    def get(self, id_: str) -> ModelT | None:
        return self.db.get(self.model, id_)

    def list(self) -> list[ModelT]:
        return self.db.query(self.model).all()

    def create(self, instance: ModelT) -> ModelT:
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def update(self, instance: ModelT, **fields) -> ModelT:
        for key, value in fields.items():
            setattr(instance, key, value)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def delete(self, instance: ModelT) -> None:
        self.db.delete(instance)
        self.db.commit()
