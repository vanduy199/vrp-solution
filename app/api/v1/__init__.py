from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.v1 import auth, depots, driver, fleet, locations, metrics, optimize, routes, users

router = APIRouter(prefix="/v1")

router.include_router(auth.router)

_protected = {"dependencies": [Depends(get_current_user)]}

router.include_router(fleet.router, tags=["Fleet & Vehicles"], **_protected)
router.include_router(depots.router, tags=["Depots"], **_protected)
router.include_router(locations.router, tags=["Locations"], **_protected)
router.include_router(users.router, tags=["Users"], **_protected)
router.include_router(optimize.router, tags=["Optimization"], **_protected)
router.include_router(routes.router, tags=["Routes"], **_protected)
router.include_router(driver.router, tags=["Driver"], **_protected)
router.include_router(metrics.router, tags=["Metrics"], **_protected)
