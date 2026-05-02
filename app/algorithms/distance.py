import math
from typing import Any


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def build_distance_matrix(points: list[Any]) -> list[list[float]]:
    """Build an n×n haversine distance matrix. Each point must have .lat and .lng."""
    return [
        [haversine(p1.lat, p1.lng, p2.lat, p2.lng) for p2 in points]
        for p1 in points
    ]
