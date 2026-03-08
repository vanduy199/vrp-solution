from fastapi import APIRouter
from app.models.request import VRPRequest
from app.service.vrp_service import solve_vrp

router = APIRouter()

@router.post("/solve")
def solve(data: VRPRequest):
    return solve_vrp(data)