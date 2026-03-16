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