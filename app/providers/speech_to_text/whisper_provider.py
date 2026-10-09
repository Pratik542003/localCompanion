from __future__ import annotations

from pathlib import Path

import httpx

from app.domain.interfaces import SpeechToText


class WhisperCppSpeechToText(SpeechToText):
    """Speech-to-text provider backed by a whisper.cpp HTTP server."""

    def __init__(self, base_url: str, timeout: int) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def transcribe(self, audio_path: Path) -> str:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            with open(audio_path, "rb") as f:
                files = {"file": (audio_path.name, f, "audio/wav")}
                response = await client.post(
                    f"{self._base_url}/inference",
                    files=files,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("text", "").strip()

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(f"{self._base_url}/health")
                return resp.status_code == 200
        except (httpx.HTTPError, Exception):
            return False
