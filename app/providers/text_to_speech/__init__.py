from __future__ import annotations

from app.domain.interfaces import TextToSpeech
from app.providers.text_to_speech.console_tts import ConsoleTextToSpeech
from app.providers.text_to_speech.piper_tts import PiperTextToSpeech

__all__ = ["ConsoleTextToSpeech", "PiperTextToSpeech", "get_text_to_speech"]


def get_text_to_speech() -> TextToSpeech:
    """Return PiperTextToSpeech if configured and binary exists, else ConsoleTextToSpeech."""
    from pathlib import Path

    from app.core.config import settings

    if settings.piper_binary_path and settings.piper_model_path:
        if Path(settings.piper_binary_path).is_file():
            return PiperTextToSpeech(
                binary_path=settings.piper_binary_path,
                model_path=settings.piper_model_path,
            )
    return ConsoleTextToSpeech()
