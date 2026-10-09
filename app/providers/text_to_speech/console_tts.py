from __future__ import annotations

from app.domain.interfaces import TextToSpeech


class ConsoleTextToSpeech(TextToSpeech):
    """Fallback TTS that prints speech text to the console."""

    async def speak(self, text: str) -> bytes | None:
        print(f"[TTS] {text}")
        return None

    def is_available(self) -> bool:
        return True
