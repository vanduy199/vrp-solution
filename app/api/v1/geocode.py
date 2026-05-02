from fastapi import APIRouter, HTTPException, Query

from app.services.map import get_map_provider

router = APIRouter(prefix="/geocode")


@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(5, ge=1, le=10),
):
    provider = get_map_provider()
    try:
        suggestions = await provider.autocomplete(q, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Map provider error: {e}")
    return [
        {
            "place_id": s.place_id,
            "display_name": s.display_name,
            "address": s.address,
            "lat": s.lat,
            "lng": s.lng,
        }
        for s in suggestions
    ]


@router.get("/place/{place_id}")
async def place_detail(place_id: str):
    provider = get_map_provider()
    try:
        detail = await provider.place_detail(place_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Map provider error: {e}")
    return {
        "place_id": detail.place_id,
        "display_name": detail.display_name,
        "address": detail.address,
        "lat": detail.lat,
        "lng": detail.lng,
    }


@router.get("/forward")
async def forward_geocode(
    address: str = Query(..., min_length=2, description="Address to geocode"),
):
    provider = get_map_provider()
    try:
        result = await provider.geocode(address)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Map provider error: {e}")
    if not result:
        raise HTTPException(status_code=404, detail="Address not found")
    return {
        "lat": result.lat,
        "lng": result.lng,
        "display_name": result.display_name,
        "address": result.address,
    }


@router.get("/reverse")
async def reverse_geocode(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
):
    provider = get_map_provider()
    try:
        result = await provider.reverse_geocode(lat, lng)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Map provider error: {e}")
    if not result:
        raise HTTPException(status_code=404, detail="Location not found")
    return {
        "lat": result.lat,
        "lng": result.lng,
        "display_name": result.display_name,
        "address": result.address,
    }
