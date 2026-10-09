from __future__ import annotations

from app.domain.interfaces import MuteController
from app.domain.models import CompanionState
from app.core.state_manager import state_manager


class SoftwareMuteController(MuteController):

    def __init__(self) -> None:
        self._muted: bool = False

    def is_muted(self) -> bool:
        return self._muted

    def mute(self) -> None:
        self._muted = True
        state_manager._state = CompanionState.MUTED

    def unmute(self) -> None:
        self._muted = False
        state_manager._state = CompanionState.ARMED


mute_controller = SoftwareMuteController()
