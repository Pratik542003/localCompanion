from __future__ import annotations

from app.providers.online_lookup.weather_provider import WeatherLookupProvider
from app.providers.online_lookup.news_provider import NewsLookupProvider

__all__ = [
    "WeatherLookupProvider",
    "NewsLookupProvider",
    "get_weather_provider",
    "get_news_provider",
]


def get_weather_provider() -> WeatherLookupProvider:
    """Return a WeatherLookupProvider with settings from config."""
    from app.core.config import settings

    return WeatherLookupProvider(
        base_url=settings.weather_provider_url,
        timeout=settings.weather_timeout,
    )


def get_news_provider() -> NewsLookupProvider:
    """Return a NewsLookupProvider with settings from config."""
    from app.core.config import settings

    return NewsLookupProvider(
        base_url=settings.news_provider_url,
        timeout=settings.news_timeout,
    )
