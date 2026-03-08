from app.utils.distance import euclidean_distance
from app.models.route import Route

class NearestNeighbor:

    def solve(self, points, depot):

        current = depot
        unvisited = [p for p in points if p.id != depot.id]

        route_path = [depot]
        total_distance = 0

        while unvisited:

            nearest = None
            min_dist = float("inf")

            for point in unvisited:

                dist = euclidean_distance(current, point)

                if dist < min_dist:
                    min_dist = dist
                    nearest = point

            route_path.append(nearest)
            total_distance += min_dist
            unvisited.remove(nearest)

            current = nearest

        # quay về depot
        dist = euclidean_distance(current, depot)
        route_path.append(depot)
        total_distance += dist

        return Route(
            vehicle_id="V1",
            path=route_path,
            distance=total_distance,
            algorithm="nearest_neighbor"
        )