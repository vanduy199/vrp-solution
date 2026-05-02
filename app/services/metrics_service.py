from sqlalchemy.orm import Session

from app.models.active_route import ActiveRoute
from app.models.route import Route
from app.models.vehicle import Vehicle


def get_dashboard_metrics(db: Session) -> dict:
    total_vehicles = db.query(Vehicle).count()
    routes = db.query(Route).all()

    active_vehicle_ids = {
        row.route.vehicle_id
        for row in db.query(ActiveRoute).all()
        if row.route
    }
    vehicles_in_use = len(active_vehicle_ids)
    utilization = round(min((vehicles_in_use / total_vehicles) * 100, 100.0), 2) if total_vehicles else 0.0

    total_distance = round(sum(float(r.total_distance_km or 0) for r in routes), 2)
    cost_savings = round(total_distance * 0.13, 2)
    trend_base = int(utilization) if utilization else 80

    return {
        "total_active_routes": db.query(ActiveRoute).count(),
        "total_vehicles": total_vehicles,
        "vehicles_in_use": vehicles_in_use,
        "vehicle_utilization_pct": utilization,
        "total_distance_km": total_distance,
        "cost_savings_usd": cost_savings,
        "efficiency_trend": [trend_base - 2, trend_base, trend_base - 1, trend_base + 1],
    }


def get_route_metrics(db: Session, route_id: str) -> dict:
    from app.services.route_service import get_route_or_404

    route = get_route_or_404(db, route_id)
    total = len(route.stops)
    from app.core.enums import StopStatus
    completed = sum(1 for s in route.stops if s.status == StopStatus.COMPLETED.value)
    completion_pct = round((completed / max(total, 1)) * 100, 2)

    return {
        "route_id": route_id,
        "status": route.status,
        "total_distance_km": route.total_distance_km,
        "total_duration_mins": route.total_duration_mins,
        "total_cost": route.total_cost,
        "stop_count": total,
        "completed_stops": completed,
        "completion_pct": completion_pct,
    }
