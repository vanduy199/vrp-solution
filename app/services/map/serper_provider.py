from __future__ import annotations

import httpx

from app.services.map.base import (
    GeocodingResult,
    MapProvider,
    PlaceDetail,
    PlaceSuggestion,
)

SERPER_BASE = "https://google.serper.dev"

_VN_PARAMS = {"gl": "vn", "hl": "vi", "location": "Vietnam"}


def _vn_query(q: str) -> str:
    """Append Vietnam context nếu chưa có để ép Serper trả kết quả trong nước."""
    lower = q.lower()
    if "việt nam" not in lower and "vietnam" not in lower and "viet nam" not in lower:
        return f"{q}, Việt Nam"
    return q


def _build_gmap_url(cid: str | None, lat: float | None, lng: float | None) -> str | None:
    if cid:
        return f"https://www.google.com/maps?cid={cid}"
    if lat is not None and lng is not None:
        return f"https://www.google.com/maps?q={lat},{lng}"
    return None


class SerperProvider(MapProvider):
    """Serper (Google Search API) implementation of MapProvider."""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("SERPER_API_KEY is required")
        self._api_key = api_key
        self._headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
        }

    async def autocomplete(self, query: str, limit: int = 5) -> list[PlaceSuggestion]:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{SERPER_BASE}/maps",
                headers=self._headers,
                json={"q": _vn_query(query), **_VN_PARAMS},
            )
            resp.raise_for_status()
            data = resp.json()

        places = data.get("places", [])[:limit]
        return [
            PlaceSuggestion(
                place_id=item.get("cid", item.get("title", "")),
                display_name=item.get("title", ""),
                address=item.get("address", item.get("title", "")),
                lat=item.get("latitude"),
                lng=item.get("longitude"),
                gmap_url=_build_gmap_url(
                    item.get("cid"),
                    item.get("latitude"),
                    item.get("longitude"),
                ),
            )
            for item in places
        ]

    async def place_detail(self, place_id: str) -> PlaceDetail:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{SERPER_BASE}/maps",
                headers=self._headers,
                json={"q": _vn_query(place_id), **_VN_PARAMS},
            )
            resp.raise_for_status()
            data = resp.json()

        places = data.get("places", [])
        if not places:
            return PlaceDetail(
                place_id=place_id,
                display_name=place_id,
                address=place_id,
            )

        item = places[0]
        return PlaceDetail(
            place_id=item.get("cid", place_id),
            display_name=item.get("title", ""),
            address=item.get("address", ""),
            lat=item.get("latitude", 0.0),
            lng=item.get("longitude", 0.0),
            gmap_url=_build_gmap_url(
                item.get("cid"),
                item.get("latitude"),
                item.get("longitude"),
            ),
            raw=item,
        )

    async def geocode(self, address: str) -> GeocodingResult | None:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{SERPER_BASE}/maps",
                headers=self._headers,
                json={"q": _vn_query(address), **_VN_PARAMS},
            )
            resp.raise_for_status()
            data = resp.json()

        places = data.get("places", [])
        if not places:
            return None

        item = places[0]
        lat = item.get("latitude")
        lng = item.get("longitude")
        if lat is None or lng is None:
            return None

        return GeocodingResult(
            lat=float(lat),
            lng=float(lng),
            display_name=item.get("title", address),
            address=item.get("address", address),
            raw=item,
        )

    async def reverse_geocode(self, lat: float, lng: float) -> GeocodingResult | None:
        query = f"{lat},{lng}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{SERPER_BASE}/maps",
                headers=self._headers,
                json={"q": query, **_VN_PARAMS},
            )
            resp.raise_for_status()
            data = resp.json()

        places = data.get("places", [])
        if not places:
            return None

        item = places[0]
        return GeocodingResult(
            lat=float(item.get("latitude", lat)),
            lng=float(item.get("longitude", lng)),
            display_name=item.get("title", query),
            address=item.get("address", query),
            raw=item,
        )
