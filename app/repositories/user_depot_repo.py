from app.models.user_depot import UserDepot
from app.repositories.base import BaseRepository


class UserDepotRepository(BaseRepository[UserDepot]):
    model = UserDepot

    def list_by_user(self, user_id: str) -> list[UserDepot]:
        return self.db.query(UserDepot).filter(UserDepot.user_id == user_id).all()

    def list_by_depot(self, depot_id: str) -> list[UserDepot]:
        return self.db.query(UserDepot).filter(UserDepot.depot_id == depot_id).all()

    def get_assignment(self, user_id: str, depot_id: str) -> UserDepot | None:
        return (
            self.db.query(UserDepot)
            .filter(UserDepot.user_id == user_id, UserDepot.depot_id == depot_id)
            .first()
        )
