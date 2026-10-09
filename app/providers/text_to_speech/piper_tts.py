from __future__ import annotations

import asyncio
from pathlib import Path

from app.domain.interfaces import TextToSpeech


class PiperTextToSpeech(TextToSpeech):
    """Text-to-speech provider using the Piper TTS binary."""

    def __init__(self, binary_path: str, model_path: str) -> None:
        self._binary_path = binary_path
        self._model_path = model_path

    async def speak(self, text: str) -> bytes | None:
        try:
            process = await asyncio.create_subprocess_exec(
                self._binary_path,
                "--model", self._model_path,
                "--output-raw",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate(input=text.encode("utf-8"))
            if process.returncode != 0:
                return None
            return stdout if stdout else None
        except Exception:
            return None

    def is_available(self) -> bool:
        return Path(self._binary_path).is_file()
