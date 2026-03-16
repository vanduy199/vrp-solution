import math


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two GPS coordinates in km
    """

    R = 6371  # Earth radius (km)

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)

    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c
def build_distance_matrix(points):

    matrix = []

    for p1 in points:

        row = []

        for p2 in points:

            dist = haversine_distance(
                p1.latitude,
                p1.longitude,
                p2.latitude,
                p2.longitude
            )

            row.append(dist)

        matrix.append(row)

    return matrix