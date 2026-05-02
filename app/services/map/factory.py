from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.services.map.base import MapProvider


@lru_cache(maxsize=1)
def get_map_provider() -> MapProvider:
    """Factory: returns the configured MapProvider singleton."""
    provider = settings.MAP_PROVIDER.lower()

    if provider == "locationiq":
        from app.services.map.locationiq_provider import LocationIQProvider
        return LocationIQProvider(api_key=settings.LOCATIONIQ_API_KEY)

    # if provider == "goong":
    #     from app.services.map.goong_provider import GoongProvider
    #     return GoongProvider(api_key=settings.GOONG_API_KEY)

    raise ValueError(
        f"Unknown MAP_PROVIDER '{settings.MAP_PROVIDER}'. "
        f"Supported: locationiq"
    )
