from __future__ import annotations

import asyncio

from app.domain.interfaces import StatusIndicator
from app.domain.models import CompanionState, STATE_COLORS


class StateManager(StatusIndicator):
    """Thread-safe manager for the companion's current state."""

    def __init__(self) -> None:
        self._state: CompanionState = CompanionState.ARMED
        self._lock = asyncio.Lock()

    async def set_state(self, state: CompanionState) -> None:
        async with self._lock:
            self._state = state

    def get_state(self) -> CompanionState:
        return self._state

    def get_color(self) -> str:
        return STATE_COLORS[self._state]


state_manager = StateManager()
