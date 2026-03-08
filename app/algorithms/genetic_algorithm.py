import random
from app.utils.distance import euclidean_distance
from app.models.route import Route


class GeneticAlgorithm:

    def __init__(self, points, depot, population_size=50, generations=200):

        self.points = points
        self.depot = depot
        self.population_size = population_size
        self.generations = generations

    def solve(self):

        customers = [p for p in self.points if p.id != self.depot.id]

        population = []

        # tạo quần thể ban đầu
        for _ in range(self.population_size):

            route = customers.copy()
            random.shuffle(route)

            population.append(route)

        best_route = None
        best_distance = float("inf")

        for _ in range(self.generations):

            new_population = []

            for route in population:

                distance = self.calculate_distance(route)

                if distance < best_distance:
                    best_distance = distance
                    best_route = route.copy()

                child = self.mutate(route.copy())

                new_population.append(child)

            population = new_population

        final_path = [self.depot] + best_route + [self.depot]

        return Route(
            vehicle_id="V1",
            path=final_path,
            distance=best_distance,
            algorithm="genetic_algorithm"
        )

    def calculate_distance(self, route):

        total = 0
        prev = self.depot

        for point in route:

            total += euclidean_distance(prev, point)
            prev = point

        total += euclidean_distance(prev, self.depot)

        return total

    def mutate(self, route):

        i, j = random.sample(range(len(route)), 2)

        route[i], route[j] = route[j], route[i]

        return route