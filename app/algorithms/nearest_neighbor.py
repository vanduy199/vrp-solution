def calculate_route_distance(route, distance_matrix):
    dist = 0
    for i in range(len(route) - 1):
        dist += distance_matrix[route[i]][route[i+1]]
    return dist

def two_opt(route, distance_matrix):
    best_route = list(route)
    best_distance = calculate_route_distance(best_route, distance_matrix)
    improved = True
    
    while improved:
        improved = False
        for i in range(1, len(best_route) - 2):
            for j in range(i + 1, len(best_route) - 1):
                node_i_minus_1 = best_route[i - 1]
                node_i = best_route[i]
                node_j = best_route[j]
                node_j_plus_1 = best_route[j + 1]
                
                # Check distance swap
                current_dist = distance_matrix[node_i_minus_1][node_i] + distance_matrix[node_j][node_j_plus_1]
                new_dist = distance_matrix[node_i_minus_1][node_j] + distance_matrix[node_i][node_j_plus_1]
                
                if new_dist < current_dist - 1e-5:
                    # Reverse the specific segment to untangle
                    best_route[i:j+1] = best_route[i:j+1][::-1]
                    best_distance -= (current_dist - new_dist)
                    improved = True
                    
    return best_route, calculate_route_distance(best_route, distance_matrix)

def nearest_neighbor(distance_matrix):
    n = len(distance_matrix)
    visited = [False] * n
    route = []
    current = 0  # depot
    route.append(current)
    visited[current] = True

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
        current = nearest
        
    route.append(0)  # Close the path
    
    # Refine greedily generated route using 2-opt
    optimized_route, optimized_distance = two_opt(route, distance_matrix)
    
    return optimized_route, optimized_distance