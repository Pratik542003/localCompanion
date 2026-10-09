from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.state_manager import state_manager
from app.core.mute_controller import mute_controller
from app.core.wake_word import get_wake_word_processor
from app.domain.interfaces import (
    MemoryRepository,
    NetworkEventRepository,
    OnlineLookupProvider,
    ReasoningProvider,
    TaskRepository,
    InteractionRepository,
)
from app.domain.models import (
    ActionType,
    CommandResponse,
    CompanionState,
    Memory,
    NetworkEvent,
    ProcessingMode,
    ReasoningResult,
    Task,
)

logger = logging.getLogger(__name__)


class CommandProcessor:
    def __init__(
        self,
        reasoning: ReasoningProvider,
        memory_repo: MemoryRepository,
        task_repo: TaskRepository,
        interaction_repo: InteractionRepository,
        network_event_repo: NetworkEventRepository,
        weather_provider: OnlineLookupProvider | None = None,
        news_provider: OnlineLookupProvider | None = None,
    ) -> None:
        self._reasoning = reasoning
        self._memory_repo = memory_repo
        self._task_repo = task_repo
        self._interaction_repo = interaction_repo
        self._network_event_repo = network_event_repo
        self._weather = weather_provider
        self._news = news_provider
        self._wake = get_wake_word_processor()

    async def process_text(self, text: str) -> CommandResponse:
        if mute_controller.is_muted():
            return CommandResponse(
                success=False,
                action="muted",
                processing_mode=ProcessingMode.LOCAL.value,
                response="The companion is currently muted.",
                state=CompanionState.MUTED.value,
            )

        passed, cleaned = self._wake.process(text)
        if not passed:
            return CommandResponse(
                success=False,
                action="no_wake_word",
                processing_mode=ProcessingMode.LOCAL.value,
                response=f'Please start your command with "{settings.wake_phrase}".',
                state=state_manager.get_state().value,
            )

        if not cleaned.strip():
            return CommandResponse(
                success=False,
                action="empty",
                processing_mode=ProcessingMode.LOCAL.value,
                response="I heard the wake phrase but no command. How can I help?",
                state=CompanionState.ARMED.value,
            )

        await state_manager.set_state(CompanionState.REASONING_LOCAL)

        await self._inject_context()

        try:
            result = await self._reasoning.reason(cleaned)
        except Exception as exc:
            logger.exception("Reasoning failed")
            await state_manager.set_state(CompanionState.ERROR)
            return CommandResponse(
                success=False,
                action="error",
                processing_mode=ProcessingMode.LOCAL.value,
                response=f"Reasoning error: {exc}",
                state=CompanionState.ERROR.value,
            )

        response = await self._execute_action(result)

        await state_manager.set_state(CompanionState.SPEAKING)
        await self._interaction_repo.record(
            result.action.value, response.processing_mode, response.response[:200]
        )
        await state_manager.set_state(CompanionState.ARMED)

        return response

    async def _execute_action(self, result: ReasoningResult) -> CommandResponse:
        handlers: dict[ActionType, Any] = {
            ActionType.SAVE_MEMORY: self._handle_save_memory,
            ActionType.SEARCH_MEMORY: self._handle_search_memory,
            ActionType.ADD_TASK: self._handle_add_task,
            ActionType.LIST_TASKS: self._handle_list_tasks,
            ActionType.COMPLETE_TASK: self._handle_complete_task,
            ActionType.WEATHER_LOOKUP: self._handle_weather,
            ActionType.NEWS_LOOKUP: self._handle_news,
            ActionType.UNSUPPORTED: self._handle_unsupported,
        }

        handler = handlers.get(result.action, self._handle_unsupported)
        return await handler(result)

    async def _handle_save_memory(self, result: ReasoningResult) -> CommandResponse:
        content = result.parameters.get("content", "")
        if not content:
            return CommandResponse(
                success=False,
                action=result.action.value,
                processing_mode=ProcessingMode.LOCAL.value,
                response="I couldn't determine what to remember. Please try again.",
                state=CompanionState.ARMED.value,
                confidence=result.confidence,
            )

        memory = Memory(
            content=content,
            normalized_content=content.lower().strip(),
            source="text",
        )
        saved = await self._memory_repo.save(memory)
        return CommandResponse(
            success=True,
            action=result.action.value,
            processing_mode=ProcessingMode.LOCAL.value,
            response=f"I've saved that to memory: \"{content}\"",
            state=CompanionState.SPEAKING.value,
            confidence=result.confidence,
        )

    async def _handle_search_memory(self, result: ReasoningResult) -> CommandResponse:
        query = result.parameters.get("query", "")
        if not query:
            return CommandResponse(
                success=False,
                action=result.action.value,
                processing_mode=ProcessingMode.LOCAL.value,
                response="I need something to search for. What would you like me to find?",
                state=CompanionState.ARMED.value,
                confidence=result.confidence,
            )

        memories = await self._memory_repo.search(query)
        if not memories:
            return CommandResponse(
                success=True,
                action=result.action.value,
                processing_mode=ProcessingMode.LOCAL.value,
                response=f"I couldn't find anything in my memory about \"{query}\".",
                state=CompanionState.SPEAKING.value,
                confidence=result.confidence,
            )

        items = "; ".join(m.content for m in memories[:5])
        return CommandResponse(
            success=True,
            action=result.action.value,
            processing_mode=ProcessingMode.LOCAL.value,
            response=f"Here's what I found: {items}",
            state=CompanionState.SPEAKING.value,
            confidence=result.confidence,
        )

    async def _handle_add_task(self, result: ReasoningResult) -> CommandResponse:
        title = result.parameters.get("title", "")
        if not title:
            return CommandResponse(
                success=False,
                action=result.action.value,
                processing_mode=ProcessingMode.LOCAL.value,
                response="I couldn't determine the task to add. Please try again.",
                state=CompanionState.ARMED.value,
                confidence=result.confidence,
            )

        task = Task(title=title, description=result.parameters.get("description", ""))
        created = await self._task_repo.create(task)
        return CommandResponse(
            success=True,
            action=result.action.value,
            processing_mode=ProcessingMode.LOCAL.value,
            response=f"I've added \"{title}\" to your task list.",
            state=CompanionState.SPEAKING.value,
            confidence=result.confidence,
        )

    async def _handle_list_tasks(self, result: ReasoningResult) -> CommandResponse:
        status_filter = result.parameters.get("status", "pending")
        tasks = await self._task_repo.get_all(status=status_filter)
        if not tasks:
            return CommandResponse(
                success=True,
                action=result.action.value,
                processing_mode=ProcessingMode.LOCAL.value,
                response=f"You have no {status_filter} tasks.",
                state=CompanionState.SPEAKING.value,
                confidence=result.confidence,
            )

        task_list = "; ".join(f"• {t.title}" for t in tasks)
        return CommandResponse(
            success=True,
            action=result.action.value,
            processing_mode=ProcessingMode.LOCAL.value,
            response=f"Your {status_filter} tasks: {task_list}",
            state=CompanionState.SPEAKING.value,
            confidence=result.confidence,
        )

    async def _handle_complete_task(self, result: ReasoningResult) -> CommandResponse:
        title = result.parameters.get("title", "")
        if not title:
            return CommandResponse(
                success=False,
                action=result.action.value,
                processing_mode=ProcessingMode.LOCAL.value,
                response="I couldn't determine which task to complete.",
                state=CompanionState.ARMED.value,
                confidence=result.confidence,
            )

        task = await self._task_repo.find_by_title(title)
        if not task:
            return CommandResponse(
                success=False,
                action=result.action.value,
                processing_mode=ProcessingMode.LOCAL.value,
                response=f"I couldn't find a task matching \"{title}\".",
                state=CompanionState.ARMED.value,
                confidence=result.confidence,
            )

        await self._task_repo.update_status(task.id, "completed")
        return CommandResponse(
            success=True,
            action=result.action.value,
            processing_mode=ProcessingMode.LOCAL.value,
            response=f"I've marked \"{task.title}\" as completed.",
            state=CompanionState.SPEAKING.value,
            confidence=result.confidence,
        )

    async def _handle_weather(self, result: ReasoningResult) -> CommandResponse:
        if not self._weather:
            return CommandResponse(
                success=False,
                action=result.action.value,
                processing_mode=ProcessingMode.LOCAL.value,
                response="Weather lookup is not configured.",
                state=CompanionState.ARMED.value,
                confidence=result.confidence,
            )

        await state_manager.set_state(CompanionState.ONLINE_LOOKUP)

        location = result.parameters.get("location", "")
        try:
            weather_data = await self._weather.lookup({"location": location})
        except Exception as exc:
            logger.exception("Weather lookup failed")
            event = NetworkEvent(
                provider=self._weather.provider_name(),
                request_type="weather",
                sanitized_query=f"location={location}",
                destination=self._weather.allowed_hostnames()[0],
                success=False,
            )
            await self._network_event_repo.record(event)
            return CommandResponse(
                success=False,
                action=result.action.value,
                processing_mode=ProcessingMode.ONLINE_LOOKUP.value,
                response=f"Weather lookup failed: {exc}",
                state=CompanionState.ERROR.value,
                confidence=result.confidence,
            )

        event = NetworkEvent(
            provider=self._weather.provider_name(),
            request_type="weather",
            sanitized_query=f"location={location}",
            destination=self._weather.allowed_hostnames()[0],
            success="error" not in weather_data,
        )
        await self._network_event_repo.record(event)

        if "error" in weather_data:
            return CommandResponse(
                success=False,
                action=result.action.value,
                processing_mode=ProcessingMode.ONLINE_LOOKUP.value,
                response=f"Weather lookup error: {weather_data['error']}",
                state=CompanionState.ERROR.value,
                confidence=result.confidence,
            )

        response_text = (
            f"[ONLINE LOOKUP] Weather in {weather_data.get('location', location)}: "
            f"{weather_data.get('condition', 'N/A')}, "
            f"{weather_data.get('temperature_c', 'N/A')}°C, "
            f"Humidity: {weather_data.get('humidity', 'N/A')}%, "
            f"Wind: {weather_data.get('wind_kmph', 'N/A')} km/h. "
            f"(Source: {weather_data.get('source', 'online')})"
        )

        return CommandResponse(
            success=True,
            action=result.action.value,
            processing_mode=ProcessingMode.ONLINE_LOOKUP.value,
            response=response_text,
            state=CompanionState.SPEAKING.value,
            confidence=result.confidence,
        )

    async def _handle_news(self, result: ReasoningResult) -> CommandResponse:
        if not self._news:
            return CommandResponse(
                success=False,
                action=result.action.value,
                processing_mode=ProcessingMode.LOCAL.value,
                response="News lookup is not configured.",
                state=CompanionState.ARMED.value,
                confidence=result.confidence,
            )

        await state_manager.set_state(CompanionState.ONLINE_LOOKUP)

        topic = result.parameters.get("topic", "")
        try:
            news_data = await self._news.lookup({"topic": topic})
        except Exception as exc:
            logger.exception("News lookup failed")
            event = NetworkEvent(
                provider=self._news.provider_name(),
                request_type="news",
                sanitized_query=f"topic={topic}",
                destination=self._news.allowed_hostnames()[0],
                success=False,
            )
            await self._network_event_repo.record(event)
            return CommandResponse(
                success=False,
                action=result.action.value,
                processing_mode=ProcessingMode.ONLINE_LOOKUP.value,
                response=f"News lookup failed: {exc}",
                state=CompanionState.ERROR.value,
                confidence=result.confidence,
            )

        event = NetworkEvent(
            provider=self._news.provider_name(),
            request_type="news",
            sanitized_query=f"topic={topic}",
            destination=self._news.allowed_hostnames()[0],
            success="error" not in news_data,
        )
        await self._network_event_repo.record(event)

        if "error" in news_data:
            return CommandResponse(
                success=False,
                action=result.action.value,
                processing_mode=ProcessingMode.ONLINE_LOOKUP.value,
                response=f"News lookup error: {news_data['error']}",
                state=CompanionState.ERROR.value,
                confidence=result.confidence,
            )

        headlines = news_data.get("headlines", [])
        if headlines:
            headline_list = "; ".join(headlines)
            response_text = (
                f"[ONLINE LOOKUP] Latest headlines: {headline_list}. "
                f"(Source: {news_data.get('source', 'online')})"
            )
        else:
            response_text = (
                f"[ONLINE LOOKUP] No headlines found"
                f"{' for topic: ' + topic if topic else ''}. "
                f"(Source: {news_data.get('source', 'online')})"
            )

        return CommandResponse(
            success=True,
            action=result.action.value,
            processing_mode=ProcessingMode.ONLINE_LOOKUP.value,
            response=response_text,
            state=CompanionState.SPEAKING.value,
            confidence=result.confidence,
        )

    async def _handle_unsupported(self, result: ReasoningResult) -> CommandResponse:
        return CommandResponse(
            success=True,
            action=ActionType.UNSUPPORTED.value,
            processing_mode=ProcessingMode.LOCAL.value,
            response="I cannot answer this reliably using my current local capabilities.",
            state=CompanionState.ARMED.value,
            confidence=result.confidence,
        )

    async def _inject_context(self) -> None:
        if hasattr(self._reasoning, "set_context"):
            try:
                memories = await self._memory_repo.get_all()
                memory_texts = [m.content for m in memories]
                tasks = await self._task_repo.get_all()
                task_dicts = [
                    {
                        "title": t.title,
                        "status": t.status if isinstance(t.status, str) else t.status.value,
                    }
                    for t in tasks
                ]
                self._reasoning.set_context(memory_texts, task_dicts)
            except Exception:
                logger.debug("Failed to inject context into reasoning provider")
