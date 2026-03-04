from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import math

app = FastAPI(title="Logistics Routing API")

# 1. Định nghĩa cấu trúc dữ liệu (Tương đương Struct)
class Point(BaseModel):
    id: str
    name: str
    x: float
    y: float

class Route(BaseModel):
    vehicle_id: str
    path: List[Point]
    distance: float

# 2. Thuật toán cốt lõi: Nearest Neighbor (Tham lam)
def calculate_nearest_neighbor(points: List[Point]) -> Route:
    if not points:
        return Route(vehicle_id="V1", path=[], distance=0.0)

    unvisited = points.copy()
    # Giả định điểm đầu tiên trong mảng truyền vào là Kho (Depot)
    current = unvisited.pop(0) 
    route_path = [current]
    total_distance = 0.0

    while unvisited:
        nearest = None
        min_dist = float('inf')
        
        for pt in unvisited:
            # Tính khoảng cách Euclid: d = sqrt((x2-x1)^2 + (y2-y1)^2)
            dist = math.sqrt((pt.x - current.x)**2 + (pt.y - current.y)**2)
            if dist < min_dist:
                min_dist = dist
                nearest = pt
        
        # Di chuyển đến điểm gần nhất
        route_path.append(nearest)
        total_distance += min_dist
        unvisited.remove(nearest)
        current = nearest
        
    return Route(vehicle_id="V1", path=route_path, distance=total_distance)

# 3. Router / API Endpoint
@app.post("/api/v1/routes", response_model=Route)
async def generate_route(points: List[Point]):
    # Nhận JSON -> Gọi thuật toán -> Trả về JSON
    # Tương lai có thể dễ dàng thay function calculate_nearest_neighbor bằng thuật toán khác
    return calculate_nearest_neighbor(points)