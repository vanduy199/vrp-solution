from app.core.enums import RouteStatus
from app.models.active_route import ActiveRoute
from app.models.route import Route
from app.repositories.base import BaseRepository


class RouteRepository(BaseRepository[Route]):
    model = Route

    def list_by_vehicle(self, vehicle_id: str) -> list[Route]:
        return self.db.query(Route).filter(Route.vehicle_id == vehicle_id).all()

    def list_by_job(self, job_id: str) -> list[Route]:
        return self.db.query(Route).filter(Route.job_id == job_id).all()

    def list_active(self) -> list[Route]:
        return (
            self.db.query(Route)
            .join(ActiveRoute, ActiveRoute.route_id == Route.id)
            .all()
        )

    def has_active_status(self, route_id: str) -> bool:
        route = self.db.get(Route, route_id)
        if not route:
            return False
        return route.status in {RouteStatus.DISPATCHED.value, RouteStatus.IN_PROGRESS.value}
