from app.models.location import Location
from app.repositories.base import BaseRepository


class LocationRepository(BaseRepository[Location]):
    model = Location

    def get_many(self, ids: list[str]) -> list[Location]:
        return self.db.query(Location).filter(Location.id.in_(ids)).all()

    def is_used_in_route(self, location_id: str) -> bool:
        from app.models.route_stop import RouteStop

        return (
            self.db.query(RouteStop)
            .filter(RouteStop.location_id == location_id)
            .first()
            is not None
        )
