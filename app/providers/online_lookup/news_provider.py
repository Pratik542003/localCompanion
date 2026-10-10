from __future__ import annotations

from typing import Any

import httpx

from app.domain.interfaces import OnlineLookupProvider
from app.core.privacy import require_lookup_url


class NewsLookupProvider(OnlineLookupProvider):
    """News lookup via Wikinews API — privacy-friendly, no API key needed."""

    def __init__(self, base_url: str = "https://en.wikinews.org", timeout: int = 10) -> None:
        self._base_url = require_lookup_url(base_url, "en.wikinews.org")
        self._timeout = timeout

    async def lookup(self, params: dict[str, Any]) -> dict[str, Any]:
        topic = params.get("topic", "")
        url = (
            f"{self._base_url}/w/api.php"
            "?action=query&list=categorymembers"
            "&cmtitle=Category:Published&cmlimit=5"
            "&cmsort=timestamp&cmdir=desc&format=json"
        )

        headers = {"User-Agent": "LocalCompanion/0.1 (offline-first assistant)"}

        try:
            async with httpx.AsyncClient(timeout=self._timeout, headers=headers) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                members = data.get("query", {}).get("categorymembers", [])
                headlines = [m.get("title", "") for m in members]

                _GENERIC = {"", "news", "headlines", "latest", "latest news", "recent news", "current news"}
                if topic and topic.lower().strip() not in _GENERIC:
                    topic_lower = topic.lower()
                    headlines = [h for h in headlines if topic_lower in h.lower()]

                return {
                    "headlines": headlines,
                    "source": "wikinews",
                    "processing_mode": "ONLINE_LOOKUP",
                }
        except Exception as e:
            return {"error": str(e), "source": "wikinews"}

    def provider_name(self) -> str:
        return "wikinews"

    def allowed_hostnames(self) -> list[str]:
        return ["en.wikinews.org"]
