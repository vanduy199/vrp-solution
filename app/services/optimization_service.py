from app.algorithms.nearest_neighbor import nearest_neighbor
from app.services.distance_service import build_distance_matrix
from app.algorithms.genetic_algorithm import genetic_algorithm

def optimize_route(points):

    distance_matrix = build_distance_matrix(points)

    route, total_distance = nearest_neighbor(distance_matrix)

    return {
        "route": route,
        "total_distance": total_distance
    }



def optimize_ga(points):

    from services.distance_service import build_distance_matrix

    distance_matrix = build_distance_matrix(points)

    route, distance = genetic_algorithm(distance_matrix)

    return {
        "route": route,
        "total_distance": distance
    }