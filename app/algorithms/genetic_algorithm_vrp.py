"""Genetic Algorithm for Multi-Vehicle VRP.

Extends GA to handle multiple vehicles simultaneously.
Chromosome represents complete VRP solution as list of routes.
"""

from __future__ import annotations

import random
from typing import Any

from app.algorithms.distance import haversine
from app.algorithms.vrp_solver import Customer, Route, Vehicle, VRPSolution


def _calculate_route_distance_matrix(
    customer_ids: list[str],
    depot_lat: float,
    depot_lng: float,
    customer_map: dict[str, Customer],
) -> dict[tuple[str, str], float]:
    """Build distance lookup for route calculation."""
    distances: dict[tuple[str, str], float] = {}

    # Depot to customers
    for cid in customer_ids:
        c = customer_map[cid]
        distances[("depot", cid)] = haversine(depot_lat, depot_lng, c.lat, c.lng)
        distances[(cid, "depot")] = distances[("depot", cid)]

    # Between customers
    for i, c1_id in enumerate(customer_ids):
        for c2_id in customer_ids[i + 1:]:
            c1 = customer_map[c1_id]
            c2 = customer_map[c2_id]
            dist = haversine(c1.lat, c1.lng, c2.lat, c2.lng)
            distances[(c1_id, c2_id)] = dist
            distances[(c2_id, c1_id)] = dist

    return distances


def _calculate_route_distance(
    customer_ids: list[str],
    depot_lat: float,
    depot_lng: float,
    distances: dict[tuple[str, str], float],
) -> float:
    """Calculate total distance for a route."""
    if not customer_ids:
        return 0.0

    total = distances[("depot", customer_ids[0])]

    for i in range(len(customer_ids) - 1):
        total += distances[(customer_ids[i], customer_ids[i + 1])]

    total += distances[(customer_ids[-1], "depot")]
    return total


class VRPGene:
    """Represents a customer's position in the VRP solution."""

    def __init__(self, customer_id: str, vehicle_id: str, position: int):
        self.customer_id = customer_id
        self.vehicle_id = vehicle_id
        self.position = position


class VRPChromosome:
    """Chromosome representing a complete VRP solution.

    Format: Dict[vehicle_id, List[customer_id]]
    Each vehicle's list represents the order of visits.
    """

    def __init__(self, routes: dict[str, list[str]]):
        self.routes = routes  # {vehicle_id: [customer_ids in order]}

    def copy(self) -> VRPChromosome:
        """Create a deep copy."""
        return VRPChromosome({k: list(v) for k, v in self.routes.items()})

    def get_all_customers(self) -> set[str]:
        """Get set of all assigned customers."""
        customers: set[str] = set()
        for route in self.routes.values():
            customers.update(route)
        return customers

    def to_vrp_solution(
        self,
        vehicles: list[Vehicle],
        customer_map: dict[str, Customer],
    ) -> VRPSolution:
        """Convert chromosome to VRPSolution."""
        vehicle_map = {v.id: v for v in vehicles}
        routes: list[Route] = []

        for vehicle_id, customer_ids in self.routes.items():
            if not customer_ids:
                continue

            vehicle = vehicle_map[vehicle_id]
            distances = _calculate_route_distance_matrix(
                customer_ids, vehicle.depot_lat, vehicle.depot_lng, customer_map
            )
            distance = _calculate_route_distance(
                customer_ids, vehicle.depot_lat, vehicle.depot_lng, distances
            )
            total_demand = sum(customer_map[cid].demand for cid in customer_ids)

            routes.append(Route(
                vehicle_id=vehicle_id,
                customer_ids=list(customer_ids),
                depot_lat=vehicle.depot_lat,
                depot_lng=vehicle.depot_lng,
                total_distance_km=distance,
                total_demand=total_demand,
            ))

        total_distance = sum(r.total_distance_km for r in routes)
        all_assigned = self.get_all_customers()

        return VRPSolution(
            routes=routes,
            total_distance_km=total_distance,
            total_vehicles_used=len(routes),
            unassigned_customers=[],
        )


def _calculate_chromosome_fitness(
    chromosome: VRPChromosome,
    vehicles: list[Vehicle],
    customer_map: dict[str, Customer],
    all_customer_ids: set[str],
) -> tuple[float, float, dict[str, Any]]:
    """Calculate fitness for a VRP chromosome.

    Returns (fitness, total_distance, info_dict).
    Fitness = 1 / (total_distance + penalties).
    """
    vehicle_map = {v.id: v for v in vehicles}
    total_distance = 0.0
    penalty = 0.0
    info: dict[str, Any] = {"violations": []}

    # Check all customers are assigned
    assigned = chromosome.get_all_customers()
    missing = all_customer_ids - assigned
    if missing:
        penalty += len(missing) * 10000  # Heavy penalty
        info["violations"].append(f"Missing customers: {missing}")

    # Check duplicates
    seen: set[str] = set()
    for vehicle_id, route in chromosome.routes.items():
        for cid in route:
            if cid in seen:
                penalty += 5000
                info["violations"].append(f"Duplicate customer: {cid}")
            seen.add(cid)

    # Calculate distances and check capacities
    for vehicle_id, route in chromosome.routes.items():
        if not route:
            continue

        vehicle = vehicle_map[vehicle_id]

        # Capacity check
        total_demand = sum(customer_map[cid].demand for cid in route)
        if total_demand > vehicle.capacity:
            excess = total_demand - vehicle.capacity
            penalty += excess * 100
            info["violations"].append(
                f"Vehicle {vehicle_id} over capacity by {excess}"
            )

        # Route distance
        distances = _calculate_route_distance_matrix(
            route, vehicle.depot_lat, vehicle.depot_lng, customer_map
        )
        route_distance = _calculate_route_distance(
            route, vehicle.depot_lat, vehicle.depot_lng, distances
        )
        total_distance += route_distance

    # Small bonus for using fewer vehicles (encourage consolidation)
    vehicles_used = len([r for r in chromosome.routes.values() if r])
    vehicle_bonus = vehicles_used * 10

    total_cost = total_distance + penalty + vehicle_bonus
    fitness = 1.0 / max(total_cost, 0.001)

    info["total_distance"] = total_distance
    info["penalty"] = penalty
    info["vehicles_used"] = vehicles_used

    return fitness, total_distance, info


def _create_initial_population_vrp(
    population_size: int,
    customers: list[Customer],
    vehicles: list[Vehicle],
) -> list[VRPChromosome]:
    """Create initial population using randomized sweep/greedy."""
    population: list[VRPChromosome] = []
    customer_ids = [c.id for c in customers]
    vehicle_ids = [v.id for v in vehicles]
    vehicle_map = {v.id: v for v in vehicles}

    for _ in range(population_size):
        # Random assignment with capacity awareness
        routes: dict[str, list[str]] = {v.id: [] for v in vehicles}
        vehicle_loads: dict[str, float] = {v.id: 0.0 for v in vehicles}

        # Shuffle customers for randomness
        shuffled = list(customer_ids)
        random.shuffle(shuffled)

        for cid in shuffled:
            customer = next(c for c in customers if c.id == cid)

            # Find vehicles with capacity
            available = [
                vid for vid in vehicle_ids
                if vehicle_loads[vid] + customer.demand <= vehicle_map[vid].capacity
            ]

            if available:
                # Random selection from available
                chosen = random.choice(available)
                routes[chosen].append(cid)
                vehicle_loads[chosen] += customer.demand

        # Shuffle order within each route (for route optimization)
        for vid in routes:
            random.shuffle(routes[vid])

        population.append(VRPChromosome(routes))

    return population


def _tournament_select_vrp(
    population: list[VRPChromosome],
    fitness_scores: list[float],
    tournament_size: int = 3,
) -> VRPChromosome:
    """Select a parent using tournament selection."""
    tournament_indices = random.sample(range(len(population)), tournament_size)
    best_idx = max(tournament_indices, key=lambda i: fitness_scores[i])
    return population[best_idx].copy()


def _crossover_vrp(
    parent1: VRPChromosome,
    parent2: VRPChromosome,
    vehicles: list[Vehicle],
) -> VRPChromosome:
    """Order Crossover (OX) adapted for VRP.

    Selects routes from parent1, fills missing customers from parent2.
    """
    vehicle_ids = [v.id for v in vehicles]

    # Start with copy of parent1's routes
    child_routes: dict[str, list[str]] = {vid: [] for vid in vehicle_ids}

    # Randomly select which vehicles to copy from parent1
    for vid in vehicle_ids:
        if vid in parent1.routes and random.random() < 0.5:
            child_routes[vid] = list(parent1.routes[vid])

    # Collect remaining customers from parent2
    assigned = set()
    for route in child_routes.values():
        assigned.update(route)

    remaining: list[str] = []
    for vid in vehicle_ids:
        if vid in parent2.routes:
            for cid in parent2.routes[vid]:
                if cid not in assigned:
                    remaining.append(cid)

    # Assign remaining customers to vehicles with space
    vehicle_map = {v.id: v for v in vehicles}

    for cid in remaining:
        # Find vehicles that aren't full yet (allow some overflow)
        available = [
            vid for vid in vehicle_ids
            if len(child_routes[vid]) < 10  # Simple heuristic: max 10 stops per vehicle
        ]

        if available:
            chosen = random.choice(available)
            child_routes[chosen].append(cid)

    return VRPChromosome(child_routes)


def _mutate_vrp(
    chromosome: VRPChromosome,
    mutation_rate: float = 0.1,
) -> VRPChromosome:
    """Apply mutation to VRP chromosome.

    Types of mutation:
    1. Swap: Exchange two customers within same route
    2. Move: Move customer to different vehicle
    3. Invert: Reverse segment of a route (2-opt-like)
    """
    mutated = chromosome.copy()
    vehicle_ids = list(mutated.routes.keys())

    if not vehicle_ids:
        return mutated

    # Mutation 1: Swap within route
    if random.random() < mutation_rate:
        vid = random.choice(vehicle_ids)
        route = mutated.routes[vid]
        if len(route) >= 2:
            i, j = random.sample(range(len(route)), 2)
            route[i], route[j] = route[j], route[i]

    # Mutation 2: Move to different vehicle
    if random.random() < mutation_rate:
        # Find vehicles with customers
        non_empty = [vid for vid in vehicle_ids if mutated.routes[vid]]
        if len(non_empty) >= 2:
            from_vid = random.choice(non_empty)
            to_vid = random.choice([v for v in vehicle_ids if v != from_vid])

            route = mutated.routes[from_vid]
            if route:
                idx = random.randint(0, len(route) - 1)
                customer = route.pop(idx)
                mutated.routes[to_vid].append(customer)

    # Mutation 3: Invert segment
    if random.random() < mutation_rate * 0.5:
        vid = random.choice(vehicle_ids)
        route = mutated.routes[vid]
        if len(route) >= 3:
            i, j = sorted(random.sample(range(len(route)), 2))
            route[i:j+1] = reversed(route[i:j+1])

    return mutated


def genetic_algorithm_vrp(
    customers: list[Customer],
    vehicles: list[Vehicle],
    population_size: int = 100,
    generations: int = 300,
    mutation_rate: float = 0.15,
    elite_size: int = 5,
    early_stopping_patience: int = 50,
) -> VRPSolution:
    """Solve VRP using Genetic Algorithm.

    Args:
        customers: List of customers to serve
        vehicles: List of available vehicles
        population_size: Size of GA population
        generations: Maximum number of generations
        mutation_rate: Probability of mutation (0-1)
        elite_size: Number of best individuals to preserve
        early_stopping_patience: Stop if no improvement for N generations

    Returns:
        VRPSolution with optimized routes
    """
    if not customers:
        return VRPSolution(
            routes=[],
            total_distance_km=0.0,
            total_vehicles_used=0,
            unassigned_customers=[],
        )

    if not vehicles:
        return VRPSolution(
            routes=[],
            total_distance_km=0.0,
            total_vehicles_used=0,
            unassigned_customers=[c.id for c in customers],
        )

    customer_map = {c.id: c for c in customers}
    all_customer_ids = {c.id for c in customers}

    # Initialize population
    population = _create_initial_population_vrp(population_size, customers, vehicles)

    best_chromosome: VRPChromosome | None = None
    best_distance = float("inf")
    best_fitness = 0.0
    generations_without_improvement = 0

    for generation in range(generations):
        # Evaluate fitness
        fitness_scores: list[float] = []
        population_with_info: list[tuple[float, float, VRPChromosome]] = []

        for chrom in population:
            fitness, distance, info = _calculate_chromosome_fitness(
                chrom, vehicles, customer_map, all_customer_ids
            )
            fitness_scores.append(fitness)
            population_with_info.append((fitness, distance, chrom))

            if distance < best_distance and info["penalty"] == 0:
                best_distance = distance
                best_chromosome = chrom.copy()
                best_fitness = fitness
                generations_without_improvement = 0

        generations_without_improvement += 1

        # Early stopping
        if generations_without_improvement >= early_stopping_patience:
            break

        # Elitism: preserve best individuals
        population_with_info.sort(key=lambda x: x[0], reverse=True)
        new_population: list[VRPChromosome] = []

        for i in range(min(elite_size, len(population_with_info))):
            new_population.append(population_with_info[i][2].copy())

        # Generate offspring
        while len(new_population) < population_size:
            parent1 = _tournament_select_vrp(population, fitness_scores)
            parent2 = _tournament_select_vrp(population, fitness_scores)
            child = _crossover_vrp(parent1, parent2, vehicles)
            child = _mutate_vrp(child, mutation_rate)
            new_population.append(child)

        population = new_population[:population_size]

    # Return best solution
    if best_chromosome:
        return best_chromosome.to_vrp_solution(vehicles, customer_map)

    # Fallback to first solution if no valid found
    if population:
        return population[0].to_vrp_solution(vehicles, customer_map)

    # Last resort: empty solution
    return VRPSolution(
        routes=[],
        total_distance_km=0.0,
        total_vehicles_used=0,
        unassigned_customers=[c.id for c in customers],
    )
