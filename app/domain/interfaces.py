from __future__ import annotations

import abc
from pathlib import Path
from typing import Any

from app.domain.models import (
    CompanionState,
    Memory,
    NetworkEvent,
    ReasoningResult,
    Task,
)


class AudioInput(abc.ABC):
    @abc.abstractmethod
    async def get_audio(self) -> bytes | None:
        ...


class SpeechToText(abc.ABC):
    @abc.abstractmethod
    async def transcribe(self, audio_path: Path) -> str:
        ...

    @abc.abstractmethod
    def is_available(self) -> bool:
        ...


class ReasoningProvider(abc.ABC):
    @abc.abstractmethod
    async def reason(self, text: str) -> ReasoningResult:
        ...

    @abc.abstractmethod
    def is_available(self) -> bool:
        ...

    @abc.abstractmethod
    def provider_name(self) -> str:
        ...


class MemoryRepository(abc.ABC):
    @abc.abstractmethod
    async def save(self, memory: Memory) -> Memory:
        ...

    @abc.abstractmethod
    async def search(self, query: str) -> list[Memory]:
        ...

    @abc.abstractmethod
    async def get_all(self) -> list[Memory]:
        ...

    @abc.abstractmethod
    async def soft_delete(self, memory_id: int) -> bool:
        ...


class TaskRepository(abc.ABC):
    @abc.abstractmethod
    async def create(self, task: Task) -> Task:
        ...

    @abc.abstractmethod
    async def get_all(self, status: str | None = None) -> list[Task]:
        ...

    @abc.abstractmethod
    async def update_status(self, task_id: int, status: str) -> bool:
        ...

    @abc.abstractmethod
    async def find_by_title(self, title: str) -> Task | None:
        ...


class InteractionRepository(abc.ABC):
    @abc.abstractmethod
    async def record(self, action: str, mode: str, summary: str) -> None:
        ...


class NetworkEventRepository(abc.ABC):
    @abc.abstractmethod
    async def record(self, event: NetworkEvent) -> None:
        ...

    @abc.abstractmethod
    async def get_all(self) -> list[NetworkEvent]:
        ...


class TextToSpeech(abc.ABC):
    @abc.abstractmethod
    async def speak(self, text: str) -> bytes | None:
        ...

    @abc.abstractmethod
    def is_available(self) -> bool:
        ...


class MuteController(abc.ABC):
    @abc.abstractmethod
    def is_muted(self) -> bool:
        ...

    @abc.abstractmethod
    def mute(self) -> None:
        ...

    @abc.abstractmethod
    def unmute(self) -> None:
        ...


class StatusIndicator(abc.ABC):
    @abc.abstractmethod
    async def set_state(self, state: CompanionState) -> None:
        ...

    @abc.abstractmethod
    def get_state(self) -> CompanionState:
        ...


class OnlineLookupProvider(abc.ABC):
    @abc.abstractmethod
    async def lookup(self, params: dict[str, Any]) -> dict[str, Any]:
        ...

    @abc.abstractmethod
    def provider_name(self) -> str:
        ...

    @abc.abstractmethod
    def allowed_hostnames(self) -> list[str]:
        ...
