from app.models.route_stop import RouteStop
from app.repositories.base import BaseRepository


class RouteStopRepository(BaseRepository[RouteStop]):
    model = RouteStop

    def list_by_route(self, route_id: str) -> list[RouteStop]:
        return (
            self.db.query(RouteStop)
            .filter(RouteStop.route_id == route_id)
            .order_by(RouteStop.sequence_index)
            .all()
        )

    def get_by_route_and_seq(self, route_id: str, sequence_index: int) -> RouteStop | None:
        return (
            self.db.query(RouteStop)
            .filter(
                RouteStop.route_id == route_id,
                RouteStop.sequence_index == sequence_index,
            )
            .first()
        )

    def delete_by_route(self, route_id: str) -> None:
        self.db.query(RouteStop).filter(RouteStop.route_id == route_id).delete()
        self.db.commit()
