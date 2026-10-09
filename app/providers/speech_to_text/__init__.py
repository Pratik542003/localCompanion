from __future__ import annotations

from app.domain.interfaces import SpeechToText
from app.providers.speech_to_text.whisper_provider import WhisperCppSpeechToText

__all__ = ["WhisperCppSpeechToText", "get_speech_to_text"]


def get_speech_to_text() -> SpeechToText | None:
    """Return a WhisperCppSpeechToText if whisper_cpp_url is configured, else None."""
    from app.core.config import settings

    if settings.whisper_cpp_url:
        return WhisperCppSpeechToText(
            base_url=settings.whisper_cpp_url,
            timeout=settings.whisper_cpp_timeout,
        )
    return None
