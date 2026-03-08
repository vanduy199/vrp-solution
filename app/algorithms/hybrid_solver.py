from app.algorithms.nearest_neighbor import NearestNeighbor
from app.algorithms.genetic_algorithm import GeneticAlgorithm

class HybridSolver:

    def __init__(self, points, depot):

        self.points = points
        self.depot = depot

    def solve(self):

        nn = NearestNeighbor()
        base_solution = nn.solve(self.points, self.depot)

        ga = GeneticAlgorithm(self.points, self.depot)

        return ga.solve_with_initial(base_solution.path)