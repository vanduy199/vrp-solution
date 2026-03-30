def validate_points(points):

    if not points:
        raise ValueError("Point list is empty")

    if len(points) < 2:
        raise ValueError("At least 2 points required")

    return True


def validate_coordinates(lat, lng):

    if lat < -90 or lat > 90:
        raise ValueError("Latitude invalid")

    if lng < -180 or lng > 180:
        raise ValueError("Longitude invalid")

    return True


def validate_demand(demand: int) -> bool:
    """Validate demand/quantity must be non-negative"""
    if demand < 0:
        raise ValueError("Demand cannot be negative")
    return True


def validate_capacity(capacity: int) -> bool:
    """Validate vehicle capacity must be non-negative"""
    if capacity < 0:
        raise ValueError("Capacity cannot be negative")
    return True


def validate_volume(volume: float) -> bool:
    """Validate volume must be non-negative"""
    if volume < 0:
        raise ValueError("Volume cannot be negative")
    return True


def validate_time_format(time_str: str) -> bool:
    """Check if string matches HH:MM format or is empty"""
    if not time_str:
        return True
    
    if not isinstance(time_str, str) or ":" not in time_str:
        return False
    
    parts = time_str.strip().split(":")
    if len(parts) != 2:
        return False
    
    try:
        hour = int(parts[0])
        minute = int(parts[1])
        return 0 <= hour < 24 and 0 <= minute < 60
    except (ValueError, TypeError):
        return False


def validate_location_input(name: str, lat: float, lng: float, demand_kg: int = 0) -> bool:
    """Validate location creation/update input"""
    if not name or not name.strip():
        raise ValueError("Location name is required")
    
    validate_coordinates(lat, lng)
    validate_demand(demand_kg)
    return True


def validate_vehicle_input(name: str, capacity_kg: int = 0, volume_m3: float = 0.0) -> bool:
    """Validate vehicle creation/update input"""
    if not name or not name.strip():
        raise ValueError("Vehicle name is required")
    
    validate_capacity(capacity_kg)
    validate_volume(volume_m3)
    return True