from fastapi import APIRouter

from app.controllers.optimization_controller import router as optimization_router
from app.controllers.router_controller import router as base_router
from app.controllers.v1_controller import router as v1_router

api_router = APIRouter()

api_router.include_router(base_router, tags=["base"])
api_router.include_router(optimization_router, tags=["optimization"])
api_router.include_router(v1_router, tags=["v1"])