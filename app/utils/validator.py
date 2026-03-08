def validate_route(route, depot):

    if route[0].id != depot.id:
        raise ValueError("Route must start at depot")

    if route[-1].id != depot.id:
        raise ValueError("Route must end at depot")

    visited = set()

    for p in route[1:-1]:

        if p.id in visited:
            raise ValueError("Duplicate point")

        visited.add(p.id)

    return True