"""
Hardware placeholders for future Raspberry Pi integration.
These classes document the interfaces that will be implemented
when physical hardware is connected. Do NOT import RPi.GPIO
or any hardware-specific libraries in the core application.
"""

from __future__ import annotations

from app.domain.interfaces import AudioInput, MuteController, StatusIndicator, TextToSpeech
from app.domain.models import CompanionState


class MicrophoneAudioInput(AudioInput):
    """Future: capture audio from USB/I2S microphone on Raspberry Pi."""

    async def get_audio(self) -> bytes | None:
        raise NotImplementedError("Hardware microphone not implemented — use AudioFileInputAdapter")


class GpioMuteController(MuteController):
    """Future: read physical toggle switch via GPIO pin."""

    def is_muted(self) -> bool:
        raise NotImplementedError("GPIO mute switch not implemented — use SoftwareMuteController")

    def mute(self) -> None:
        raise NotImplementedError

    def unmute(self) -> None:
        raise NotImplementedError


class GpioLedIndicator(StatusIndicator):
    """Future: drive RGB LED strip via GPIO to show companion state colors."""

    async def set_state(self, state: CompanionState) -> None:
        raise NotImplementedError("GPIO LED indicator not implemented — use WebStatusIndicator")

    def get_state(self) -> CompanionState:
        raise NotImplementedError


class SpeakerOutput(TextToSpeech):
    """Future: play audio through connected speaker on Raspberry Pi."""

    async def speak(self, text: str) -> bytes | None:
        raise NotImplementedError("Speaker output not implemented — use ConsoleTextToSpeech or PiperTextToSpeech")

    def is_available(self) -> bool:
        return False
