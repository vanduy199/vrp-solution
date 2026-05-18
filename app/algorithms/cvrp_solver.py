"""Capacitated VRP (CVRP) Solver.

Implements cluster-first route-second approach with capacity constraints:
1. Sweep algorithm for initial clustering
2. TSP optimization for each cluster/route
"""

from __future__ import annotations

import math
from typing import Any

from app.algorithms.distance import haversine
from app.algorithms.nearest_neighbor import two_opt
from app.algorithms.vrp_solver import (
    Customer,
    Route,
    Vehicle,
    VRPSolution,
    calculate_route_distance,
)


def _calculate_polar_angle(
    depot_lat: float,
    depot_lng: float,
    customer: Customer,
) -> float:
    """Calculate polar angle of customer relative to depot.

    Returns angle in radians [0, 2*pi).
    """
    dy = customer.lat - depot_lat
    dx = customer.lng - depot_lng
    return math.atan2(dy, dx) % (2 * math.pi)


def _sort_by_polar_angle(
    customers: list[Customer],
    depot_lat: float,
    depot_lng: float,
) -> list[Customer]:
    """Sort customers by polar angle from depot."""
    return sorted(
        customers,
        key=lambda c: _calculate_polar_angle(depot_lat, depot_lng, c),
    )


def _build_route_distance_matrix(
    customer_ids: list[str],
    depot_lat: float,
    depot_lng: float,
    customer_map: dict[str, Customer],
) -> list[list[float]]:
    """Build distance matrix for a single route (depot + customers).

    Matrix indices: 0 = depot, 1..n = customers
    """
    points = [(depot_lat, depot_lng)]  # Index 0 is depot
    for cid in customer_ids:
        c = customer_map[cid]
        points.append((c.lat, c.lng))

    n = len(points)
    matrix = [[0.0] * n for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i != j:
                matrix[i][j] = haversine(
                    points[i][0], points[i][1],
                    points[j][0], points[j][1]
                )

    return matrix


def _optimize_route_with_2opt(
    route: Route,
    customer_map: dict[str, Customer],
) -> Route:
    """Apply 2-opt improvement to a route."""
    if len(route.customer_ids) <= 1:
        route.total_distance_km = calculate_route_distance(route, customer_map)
        return route

    # Build distance matrix for TSP
    matrix = _build_route_distance_matrix(
        route.customer_ids, route.depot_lat, route.depot_lng, customer_map
    )

    # Current route as indices (0 = depot, 1..n = customers in order)
    current_route = list(range(len(matrix)))
    current_route.append(0)  # Return to depot

    # Apply 2-opt
    optimized, distance = two_opt(current_route, matrix)

    # Convert back to customer IDs (skip depot indices 0)
    optimized_customer_ids = []
    for idx in optimized[1:-1]:  # Skip first and last (depot)
        if 1 <= idx <= len(route.customer_ids):
            optimized_customer_ids.append(route.customer_ids[idx - 1])

    return Route(
        vehicle_id=route.vehicle_id,
        customer_ids=optimized_customer_ids,
        depot_lat=route.depot_lat,
        depot_lng=route.depot_lng,
        total_distance_km=distance,
        total_demand=route.total_demand,
    )


class SweepCVRPSolver:
    """CVRP solver using Sweep algorithm.

    Algorithm:
    1. Calculate polar angle for each customer relative to depot
    2. Sort customers by angle
    3. Assign to vehicles in sweep order, respecting capacity
    4. Optimize each route with 2-opt
    """

    def solve(
        self,
        customers: list[Customer],
        vehicles: list[Vehicle],
    ) -> VRPSolution:
        """Solve CVRP using sweep algorithm.

        Args:
            customers: List of customers to serve
            vehicles: List of available vehicles

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

        # Use first vehicle's depot as reference
        # (assumes all vehicles share depot or we handle multiple depots)
        depot_lat = vehicles[0].depot_lat
        depot_lng = vehicles[0].depot_lng

        # Sort customers by polar angle
        sorted_customers = _sort_by_polar_angle(customers, depot_lat, depot_lng)

        # Initialize routes for each vehicle
        routes: list[Route] = []
        for v in vehicles:
            routes.append(Route(
                vehicle_id=v.id,
                customer_ids=[],
                depot_lat=v.depot_lat,
                depot_lng=v.depot_lng,
                total_distance_km=0.0,
                total_demand=0.0,
            ))

        # Assign customers using sweep
        vehicle_idx = 0
        unassigned: list[str] = []
        customer_map = {c.id: c for c in customers}

        for customer in sorted_customers:
            assigned = False
            attempts = 0

            # Try to assign to current or subsequent vehicles
            start_idx = vehicle_idx
            while attempts < len(vehicles):
                v_idx = (start_idx + attempts) % len(vehicles)
                vehicle = vehicles[v_idx]
                route = routes[v_idx]

                # Check capacity constraint (0 = unlimited)
                new_demand = route.total_demand + customer.demand
                if vehicle.capacity == 0 or new_demand <= vehicle.capacity:
                    route.customer_ids.append(customer.id)
                    route.total_demand = new_demand
                    vehicle_idx = v_idx  # Continue with this vehicle
                    assigned = True
                    break

                attempts += 1

            if not assigned:
                unassigned.append(customer.id)

        # Optimize each route with 2-opt
        optimized_routes: list[Route] = []
        for route in routes:
            if route.customer_ids:
                optimized = _optimize_route_with_2opt(route, customer_map)
                optimized.total_demand = sum(
                    customer_map[cid].demand for cid in optimized.customer_ids
                )
                optimized_routes.append(optimized)

        # Calculate total distance
        total_distance = sum(r.total_distance_km for r in optimized_routes)

        return VRPSolution(
            routes=optimized_routes,
            total_distance_km=total_distance,
            total_vehicles_used=len(optimized_routes),
            unassigned_customers=unassigned,
        )


class GreedyCVRPSolver:
    """Greedy CVRP solver - assigns customers to nearest available vehicle with capacity.

    Algorithm:
    1. For each unassigned customer
    2. Find the nearest vehicle (by depot distance) with available capacity
    3. Assign customer to that vehicle
    4. After all assignments, optimize routes with TSP
    """

    def solve(
        self,
        customers: list[Customer],
        vehicles: list[Vehicle],
    ) -> VRPSolution:
        """Solve CVRP using greedy assignment + TSP optimization."""
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
        vehicle_map = {v.id: v for v in vehicles}

        # Initialize empty routes
        routes: dict[str, Route] = {}
        vehicle_loads: dict[str, float] = {}

        for v in vehicles:
            routes[v.id] = Route(
                vehicle_id=v.id,
                customer_ids=[],
                depot_lat=v.depot_lat,
                depot_lng=v.depot_lng,
                total_distance_km=0.0,
                total_demand=0.0,
            )
            vehicle_loads[v.id] = 0.0

        # Sort customers by demand (largest first for better packing)
        sorted_customers = sorted(customers, key=lambda c: c.demand, reverse=True)

        unassigned: list[str] = []

        for customer in sorted_customers:
            # Find best vehicle (nearest depot with capacity)
            best_vehicle: str | None = None
            best_distance = float("inf")

            for v in vehicles:
                current_load = vehicle_loads[v.id]
                if v.capacity == 0 or current_load + customer.demand <= v.capacity:
                    # Distance from vehicle depot to customer
                    dist = haversine(v.depot_lat, v.depot_lng, customer.lat, customer.lng)
                    if dist < best_distance:
                        best_distance = dist
                        best_vehicle = v.id

            if best_vehicle:
                routes[best_vehicle].customer_ids.append(customer.id)
                vehicle_loads[best_vehicle] += customer.demand
                routes[best_vehicle].total_demand = vehicle_loads[best_vehicle]
            else:
                unassigned.append(customer.id)

        # Optimize each route
        optimized_routes: list[Route] = []
        for route in routes.values():
            if route.customer_ids:
                optimized = _optimize_route_with_2opt(route, customer_map)
                optimized.total_demand = sum(
                    customer_map[cid].demand for cid in optimized.customer_ids
                )
                optimized_routes.append(optimized)

        total_distance = sum(r.total_distance_km for r in optimized_routes)

        return VRPSolution(
            routes=optimized_routes,
            total_distance_km=total_distance,
            total_vehicles_used=len(optimized_routes),
            unassigned_customers=unassigned,
        )


def solve_cvrp(
    customers: list[Customer],
    vehicles: list[Vehicle],
    algorithm: str = "sweep",
) -> VRPSolution:
    """Solve CVRP with specified algorithm.

    Args:
        customers: List of customers to serve
        vehicles: List of available vehicles with capacities
        algorithm: "sweep" or "greedy"

    Returns:
        VRPSolution with optimized routes
    """
    if algorithm == "sweep":
        solver = SweepCVRPSolver()
    elif algorithm == "greedy":
        solver = GreedyCVRPSolver()
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    return solver.solve(customers, vehicles)
