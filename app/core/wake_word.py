from __future__ import annotations

import re


class WakeWordProcessor:
    """Detects and strips a wake phrase from the beginning of text input."""

    def __init__(self, wake_phrase: str, enabled: bool) -> None:
        self._wake_phrase = wake_phrase
        self._enabled = enabled

    def process(self, text: str) -> tuple[bool, str]:
        """Check for the wake phrase and return (detected, remaining_text).

        If wake word detection is disabled, all text passes through.
        """
        stripped = text.lstrip()
        if re.match(rf"{re.escape(self._wake_phrase)}(?:\b|$)", stripped, flags=re.I):
            remaining = stripped[len(self._wake_phrase) :]
            # Strip common punctuation that may follow the wake phrase
            remaining = re.sub(r"^[,;:!?\-\s]+", "", remaining)
            return True, remaining.strip()

        if not self._enabled:
            return True, text

        return False, ""


def get_wake_word_processor() -> WakeWordProcessor:
    """Factory that builds a WakeWordProcessor from application settings."""
    from app.core.config import settings

    return WakeWordProcessor(
        wake_phrase=settings.wake_phrase,
        enabled=settings.wake_word_enabled,
    )
