def nearest_neighbor(distance_matrix):

    n = len(distance_matrix)

    visited = [False] * n

    route = []

    current = 0  # depot

    route.append(current)

    visited[current] = True

    total_distance = 0

    for _ in range(n - 1):

        nearest = None
        nearest_dist = float("inf")

        for i in range(n):

            if not visited[i]:

                dist = distance_matrix[current][i]

                if dist < nearest_dist:
                    nearest = i
                    nearest_dist = dist

        route.append(nearest)

        visited[nearest] = True

        total_distance += nearest_dist

        current = nearest

    total_distance += distance_matrix[current][0]

    route.append(0)

    return route, total_distance