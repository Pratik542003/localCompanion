from __future__ import annotations

from pathlib import Path

import httpx

from app.domain.interfaces import SpeechToText
from app.core.privacy import require_local_url


class WhisperCppSpeechToText(SpeechToText):
    """Speech-to-text provider backed by a whisper.cpp HTTP server."""

    def __init__(self, base_url: str, timeout: int) -> None:
        self._base_url = require_local_url(base_url)
        self._timeout = timeout

    async def transcribe(self, audio_path: Path) -> str:
        async with httpx.AsyncClient(timeout=self._timeout, trust_env=False) as client:
            with open(audio_path, "rb") as f:
                files = {"file": (audio_path.name, f, "audio/wav")}
                response = await client.post(
                    f"{self._base_url}/inference",
                    files=files, data={"response_format": "json", "temperature": "0", "language": "en"},
                )
                response.raise_for_status()
                data = response.json()
                return data.get("text", "").strip()

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=3, trust_env=False) as client:
                resp = client.get(f"{self._base_url}/health")
                return resp.status_code == 200
        except (httpx.HTTPError, Exception):
            return False
