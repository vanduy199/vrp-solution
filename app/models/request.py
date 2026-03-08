from pydantic import BaseModel
from typing import List
from app.models.point import Point

class VRPRequest(BaseModel):
    depot: Point
    points: List[Point]
    algorithm: str