from database.repositories import get_points


def list_points(db):

    points = get_points(db)

    return {
        "success": True,
        "data": points
    }