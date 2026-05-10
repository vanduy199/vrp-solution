"""Unified VRP Solver Interface.

This module provides the main interface for solving Vehicle Routing Problems (VRP),
supporting multiple algorithms and constraint types.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.algorithms.distance import build_distance_matrix, haversine


@dataclass
class Customer:
    """Customer/location data for VRP."""

    id: str
    lat: float
    lng: float
    demand: float = 0.0


@dataclass
class Vehicle:
    """Vehicle data for VRP."""

    id: str
    capacity: float
    depot_lat: float
    depot_lng: float
    cost_per_km: float = 1.0


@dataclass
class Route:
    """A single vehicle route."""

    vehicle_id: str
    customer_ids: list[str]
    depot_lat: float
    depot_lng: float
    total_distance_km: float = 0.0
    total_demand: float = 0.0


@dataclass
class VRPSolution:
    """Complete VRP solution with multiple routes."""

    routes: list[Route]
    total_distance_km: float
    total_vehicles_used: int
    unassigned_customers: list[str]

    def __post_init__(self):
        """Validate solution."""
        self.total_vehicles_used = len([r for r in self.routes if r.customer_ids])


class VRPSolver(Protocol):
    """Protocol for VRP solver implementations."""

    def solve(
        self,
        customers: list[Customer],
        vehicles: list[Vehicle],
    ) -> VRPSolution:
        """Solve VRP and return solution.

        Args:
            customers: List of customers to serve
            vehicles: List of available vehicles

        Returns:
            VRPSolution containing optimized routes
        """
        ...


def calculate_route_distance(
    route: Route,
    customer_map: dict[str, Customer],
) -> float:
    """Calculate total distance for a route.

    Args:
        route: Route to calculate
        customer_map: Map of customer_id -> Customer

    Returns:
        Total distance in km
    """
    if not route.customer_ids:
        return 0.0

    total = 0.0

    # Depot to first customer
    first_cust = customer_map[route.customer_ids[0]]
    total += haversine(route.depot_lat, route.depot_lng, first_cust.lat, first_cust.lng)

    # Between customers
    for i in range(len(route.customer_ids) - 1):
        c1 = customer_map[route.customer_ids[i]]
        c2 = customer_map[route.customer_ids[i + 1]]
        total += haversine(c1.lat, c1.lng, c2.lat, c2.lng)

    # Last customer to depot
    last_cust = customer_map[route.customer_ids[-1]]
    total += haversine(last_cust.lat, last_cust.lng, route.depot_lat, route.depot_lng)

    return total


def validate_vrp_solution(
    solution: VRPSolution,
    customers: list[Customer],
    vehicles: list[Vehicle],
) -> dict[str, Any]:
    """Validate a VRP solution.

    Returns dict with validation results and any errors.
    """
    customer_map = {c.id: c for c in customers}
    vehicle_map = {v.id: v for v in vehicles}

    errors = []
    warnings = []

    # Check all customers are assigned
    assigned_customers = set()
    for route in solution.routes:
        for cid in route.customer_ids:
            if cid in assigned_customers:
                errors.append(f"Customer {cid} assigned to multiple routes")
            assigned_customers.add(cid)

    all_customer_ids = {c.id for c in customers}
    unassigned = all_customer_ids - assigned_customers
    if unassigned:
        warnings.append(f"Unassigned customers: {unassigned}")

    # Check capacity constraints
    for route in solution.routes:
        if not route.customer_ids:
            continue

        vehicle = vehicle_map.get(route.vehicle_id)
        if not vehicle:
            errors.append(f"Route references unknown vehicle {route.vehicle_id}")
            continue

        total_demand = sum(customer_map[cid].demand for cid in route.customer_ids)
        if total_demand > vehicle.capacity:
            errors.append(
                f"Vehicle {route.vehicle_id} overloaded: "
                f"{total_demand} > {vehicle.capacity}"
            )

    # Check route distances
    for route in solution.routes:
        if not route.customer_ids:
            continue

        actual_distance = calculate_route_distance(route, customer_map)
        if abs(actual_distance - route.total_distance_km) > 0.01:
            warnings.append(
                f"Route {route.vehicle_id} distance mismatch: "
                f"stored={route.total_distance_km:.2f}, actual={actual_distance:.2f}"
            )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "total_customers": len(customers),
        "assigned_customers": len(assigned_customers),
        "unassigned_customers": list(unassigned),
    }
