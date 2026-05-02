from app.core.enums import VehicleStatus
from app.models.vehicle import Vehicle
from app.repositories.base import BaseRepository


class VehicleRepository(BaseRepository[Vehicle]):
    model = Vehicle

    def list_by_depot(self, depot_id: str) -> list[Vehicle]:
        return self.db.query(Vehicle).filter(Vehicle.depot_id == depot_id).all()

    def list_available(self) -> list[Vehicle]:
        return (
            self.db.query(Vehicle)
            .filter(Vehicle.status == VehicleStatus.AVAILABLE.value)
            .all()
        )

    def has_active_routes(self, vehicle_id: str) -> bool:
        from app.models.active_route import ActiveRoute
        from app.models.route import Route

        return (
            self.db.query(Route)
            .join(ActiveRoute, ActiveRoute.route_id == Route.id)
            .filter(Route.vehicle_id == vehicle_id)
            .first()
            is not None
        )
