from pydantic import BaseModel
from typing import List
from app.models.point import Point

class Route(BaseModel):
    vehicle_id: str
    path: List[Point]
    distance: float
    algorithm: str