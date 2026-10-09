from __future__ import annotations

from app.providers.online_lookup.weather_provider import WeatherLookupProvider

__all__ = ["WeatherLookupProvider", "get_weather_provider"]


def get_weather_provider() -> WeatherLookupProvider:
    """Return a WeatherLookupProvider with settings from config."""
    from app.core.config import settings

    return WeatherLookupProvider(
        base_url=settings.weather_provider_url,
        timeout=settings.weather_timeout,
    )
