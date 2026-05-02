from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class PlaceSuggestion:
    place_id: str
    display_name: str
    address: str
    lat: float | None = None
    lng: float | None = None


@dataclass
class PlaceDetail:
    place_id: str
    display_name: str
    address: str
    lat: float = 0.0
    lng: float = 0.0
    raw: dict = field(default_factory=dict)


@dataclass
class GeocodingResult:
    lat: float
    lng: float
    display_name: str
    address: str
    raw: dict = field(default_factory=dict)


class MapProvider(ABC):
    """Abstract interface for map/geocoding providers."""

    @abstractmethod
    async def autocomplete(self, query: str, limit: int = 5) -> list[PlaceSuggestion]:
        """Return place suggestions matching the query string."""
        ...

    @abstractmethod
    async def place_detail(self, place_id: str) -> PlaceDetail:
        """Return full details (including lat/lng) for a place_id."""
        ...

    @abstractmethod
    async def geocode(self, address: str) -> GeocodingResult | None:
        """Convert an address string to coordinates."""
        ...

    @abstractmethod
    async def reverse_geocode(self, lat: float, lng: float) -> GeocodingResult | None:
        """Convert coordinates to an address."""
        ...
