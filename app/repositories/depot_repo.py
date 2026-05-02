from app.models.depot import Depot
from app.repositories.base import BaseRepository


class DepotRepository(BaseRepository[Depot]):
    model = Depot

    def first(self) -> Depot | None:
        return self.db.query(Depot).first()
