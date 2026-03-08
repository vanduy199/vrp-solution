from app.algorithms.nearest_neighbor import NearestNeighbor
from app.algorithms.genetic_algorithm import GeneticAlgorithm
from app.models.route import Route

def solve_vrp(data):

    points = [data.depot] + data.points

    if data.algorithm == "nearest_neighbor":

        solver = NearestNeighbor()
        result = solver.solve(points, data.depot)

    elif data.algorithm == "genetic":

        solver = GeneticAlgorithm(points, data.depot)
        result = solver.solve()

    else:
        raise ValueError("Unsupported algorithm")

    return result