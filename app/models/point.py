from pydantic import BaseModel

class Point(BaseModel):
    id: str
    name: str
    x: float
    y: float