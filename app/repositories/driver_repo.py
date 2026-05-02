from app.models.driver import Driver
from app.repositories.base import BaseRepository


class DriverRepository(BaseRepository[Driver]):
    model = Driver

    def list_by_depot(self, depot_id: str) -> list[Driver]:
        return self.db.query(Driver).filter(Driver.depot_id == depot_id).all()

    def list_by_admin(self, admin_id: str) -> list[Driver]:
        return self.db.query(Driver).filter(Driver.admin_id == admin_id).all()
