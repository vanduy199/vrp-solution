from __future__ import annotations

import httpx

from app.services.map.base import (
    GeocodingResult,
    MapProvider,
    PlaceDetail,
    PlaceSuggestion,
)

LOCATIONIQ_BASE = "https://us1.locationiq.com/v1"


class LocationIQProvider(MapProvider):
    """LocationIQ implementation of MapProvider."""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("LOCATIONIQ_API_KEY is required")
        self._api_key = api_key

    async def autocomplete(self, query: str, limit: int = 5) -> list[PlaceSuggestion]:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{LOCATIONIQ_BASE}/autocomplete",
                params={
                    "key": self._api_key,
                    "q": query,
                    "limit": limit,
                    "format": "json",
                    "countrycodes": "vn",
                    "accept-language": "vi",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return [
            PlaceSuggestion(
                place_id=item.get("place_id", ""),
                display_name=item.get("display_name", ""),
                address=item.get("display_name", ""),
                lat=float(item["lat"]) if item.get("lat") else None,
                lng=float(item["lon"]) if item.get("lon") else None,
            )
            for item in data
        ]

    async def place_detail(self, place_id: str) -> PlaceDetail:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{LOCATIONIQ_BASE}/reverse",
                params={
                    "key": self._api_key,
                    "osm_id": place_id,
                    "osm_type": "N",
                    "format": "json",
                    "accept-language": "vi",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return PlaceDetail(
            place_id=str(data.get("place_id", place_id)),
            display_name=data.get("display_name", ""),
            address=data.get("display_name", ""),
            lat=float(data.get("lat", 0)),
            lng=float(data.get("lon", 0)),
            raw=data,
        )

    async def geocode(self, address: str) -> GeocodingResult | None:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{LOCATIONIQ_BASE}/search",
                params={
                    "key": self._api_key,
                    "q": address,
                    "format": "json",
                    "limit": 1,
                    "countrycodes": "vn",
                    "accept-language": "vi",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        if not data:
            return None

        item = data[0]
        return GeocodingResult(
            lat=float(item["lat"]),
            lng=float(item["lon"]),
            display_name=item.get("display_name", ""),
            address=item.get("display_name", ""),
            raw=item,
        )

    async def reverse_geocode(self, lat: float, lng: float) -> GeocodingResult | None:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{LOCATIONIQ_BASE}/reverse",
                params={
                    "key": self._api_key,
                    "lat": lat,
                    "lon": lng,
                    "format": "json",
                    "accept-language": "vi",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        if not data or "error" in data:
            return None

        return GeocodingResult(
            lat=float(data.get("lat", lat)),
            lng=float(data.get("lon", lng)),
            display_name=data.get("display_name", ""),
            address=data.get("display_name", ""),
            raw=data,
        )
