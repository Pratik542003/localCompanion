from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CompanionState(str, enum.Enum):
    MUTED = "MUTED"
    ARMED = "ARMED"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    REASONING_LOCAL = "REASONING_LOCAL"
    ONLINE_LOOKUP = "ONLINE_LOOKUP"
    SPEAKING = "SPEAKING"
    ERROR = "ERROR"


STATE_COLORS: dict[CompanionState, str] = {
    CompanionState.MUTED: "#9E9E9E",
    CompanionState.ARMED: "#2196F3",
    CompanionState.LISTENING: "#4CAF50",
    CompanionState.TRANSCRIBING: "#FFEB3B",
    CompanionState.REASONING_LOCAL: "#9C27B0",
    CompanionState.ONLINE_LOOKUP: "#FF9800",
    CompanionState.SPEAKING: "#00BCD4",
    CompanionState.ERROR: "#F44336",
}


class ProcessingMode(str, enum.Enum):
    LOCAL = "LOCAL"
    ONLINE_LOOKUP = "ONLINE_LOOKUP"


class ActionType(str, enum.Enum):
    SAVE_MEMORY = "save_memory"
    SEARCH_MEMORY = "search_memory"
    ADD_TASK = "add_task"
    LIST_TASKS = "list_tasks"
    COMPLETE_TASK = "complete_task"
    WEATHER_LOOKUP = "weather_lookup"
    NEWS_LOOKUP = "news_lookup"
    UNSUPPORTED = "unsupported"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"


class ReasoningResult(BaseModel):
    action: ActionType
    parameters: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)
    response: str


class Memory(BaseModel):
    id: int | None = None
    content: str
    normalized_content: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    source: str = "text"
    deleted_at: datetime | None = None


class Task(BaseModel):
    id: int | None = None
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    due_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Interaction(BaseModel):
    id: int | None = None
    detected_action: str
    processing_mode: str
    response_summary: str
    created_at: datetime | None = None


class NetworkEvent(BaseModel):
    id: int | None = None
    provider: str
    request_type: str
    sanitized_query: str
    destination: str
    success: bool
    created_at: datetime | None = None


class CommandRequest(BaseModel):
    text: str


class CommandResponse(BaseModel):
    success: bool
    action: str
    processing_mode: str
    response: str
    state: str
    confidence: float = 0.0


class AudioUploadResponse(BaseModel):
    success: bool
    transcription: str | None = None
    action: str | None = None
    processing_mode: str | None = None
    response: str | None = None
    state: str | None = None
    error: str | None = None
