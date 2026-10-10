from __future__ import annotations

from typing import Any

import httpx

from app.domain.interfaces import OnlineLookupProvider
from app.core.privacy import require_lookup_url


class WeatherLookupProvider(OnlineLookupProvider):
    """Weather lookup via wttr.in — only sends location, never personal data."""

    def __init__(self, base_url: str, timeout: int) -> None:
        self._base_url = require_lookup_url(base_url, "wttr.in")
        self._timeout = timeout

    async def lookup(self, params: dict[str, Any]) -> dict[str, Any]:
        location = params.get("location", "London")
        url = f"{self._base_url}/{location}?format=j1"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                current = data.get("current_condition", [{}])[0]
                desc_list = current.get("weatherDesc", [{}])
                description = desc_list[0].get("value", "") if desc_list else ""

                return {
                    "location": location,
                    "temperature_c": current.get("temp_C", ""),
                    "condition": description,
                    "humidity": current.get("humidity", ""),
                    "wind_kmph": current.get("windspeedKmph", ""),
                    "source": "wttr.in",
                    "processing_mode": "ONLINE_LOOKUP",
                }
        except Exception as e:
            return {"error": str(e), "source": "wttr.in"}

    def provider_name(self) -> str:
        return "wttr.in"

    def allowed_hostnames(self) -> list[str]:
        return ["wttr.in"]
