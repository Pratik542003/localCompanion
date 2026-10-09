from __future__ import annotations

import re

from app.domain.interfaces import ReasoningProvider
from app.domain.models import ActionType, ReasoningResult


class DemoReasoningProvider(ReasoningProvider):
    """Deterministic keyword-based reasoning provider for demo/offline mode."""

    # Ordered list of (action, keywords, needs_extraction) tuples.
    # Order matters: more specific patterns are checked first.
    _RULES: list[tuple[ActionType, list[str]]] = [
        (ActionType.LIST_TASKS, [
            "show tasks", "list tasks", "pending tasks", "my tasks", "show my",
        ]),
        (ActionType.COMPLETE_TASK, [
            "mark", "complete", "finish", "done with",
        ]),
        (ActionType.ADD_TASK, [
            "add to my task list", "add to task", "create task", "new task", "add task", "add",
        ]),
        (ActionType.SAVE_MEMORY, [
            "keep in mind", "note that", "remember", "save", "store",
        ]),
        (ActionType.WEATHER_LOOKUP, [
            "weather", "temperature", "forecast",
        ]),
        (ActionType.SEARCH_MEMORY, [
            "do you remember", "what do you know about",
            "when is", "what is", "recall", "find", "search",
        ]),
    ]

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract_after_keyword(text: str, keyword: str) -> str:
        idx = text.find(keyword)
        if idx == -1:
            return text.strip()
        return text[idx + len(keyword):].strip().strip(".")

    @staticmethod
    def _clean_task_title(text: str) -> str:
        cleaned = re.sub(
            r"\s+(to my task list|to my tasks|to task list|to tasks|to my list)\s*$",
            "", text,
        )
        cleaned = re.sub(r"\s+(as completed|as done|as finished)\s*$", "", cleaned)
        return cleaned.strip().strip(".")

    @staticmethod
    def _extract_location(text: str) -> str:
        match = re.search(r"\bin\s+(.+?)(?:\?|$)", text)
        if match:
            return match.group(1).strip().rstrip(".")
        return ""

    # ------------------------------------------------------------------ #
    # Interface
    # ------------------------------------------------------------------ #

    async def reason(self, text: str) -> ReasoningResult:
        lower = text.lower().strip()

        for action, keywords in self._RULES:
            # Sort keywords longest-first so the most specific phrase wins.
            for kw in sorted(keywords, key=len, reverse=True):
                if kw in lower:
                    return self._build_result(action, text, lower, kw)

        # Nothing matched -> unsupported
        return ReasoningResult(
            action=ActionType.UNSUPPORTED,
            parameters={},
            confidence=1.0,
            response="I cannot answer this reliably using my current local capabilities.",
        )

    def is_available(self) -> bool:
        return True

    def provider_name(self) -> str:
        return "demo"

    # ------------------------------------------------------------------ #
    # Result builders
    # ------------------------------------------------------------------ #

    def _build_result(
        self,
        action: ActionType,
        original: str,
        lower: str,
        matched_keyword: str,
    ) -> ReasoningResult:
        if action == ActionType.SAVE_MEMORY:
            content = self._extract_after_keyword(lower, matched_keyword)
            return ReasoningResult(
                action=ActionType.SAVE_MEMORY,
                parameters={"content": content or original.strip()},
                confidence=0.95,
                response="I've saved that to memory.",
            )

        if action == ActionType.SEARCH_MEMORY:
            query = self._extract_after_keyword(lower, matched_keyword)
            return ReasoningResult(
                action=ActionType.SEARCH_MEMORY,
                parameters={"query": query or lower},
                confidence=0.90,
                response="Let me search my memory.",
            )

        if action == ActionType.ADD_TASK:
            title = self._extract_after_keyword(lower, matched_keyword)
            title = self._clean_task_title(title)
            return ReasoningResult(
                action=ActionType.ADD_TASK,
                parameters={"title": title or original.strip()},
                confidence=0.92,
                response="I've added that to your task list.",
            )

        if action == ActionType.LIST_TASKS:
            return ReasoningResult(
                action=ActionType.LIST_TASKS,
                parameters={},
                confidence=0.95,
                response="Here are your tasks.",
            )

        if action == ActionType.COMPLETE_TASK:
            title = self._extract_after_keyword(lower, matched_keyword)
            title = self._clean_task_title(title)
            return ReasoningResult(
                action=ActionType.COMPLETE_TASK,
                parameters={"title": title or original.strip()},
                confidence=0.90,
                response="I've marked that task as completed.",
            )

        if action == ActionType.WEATHER_LOOKUP:
            location = self._extract_location(lower)
            return ReasoningResult(
                action=ActionType.WEATHER_LOOKUP,
                parameters={"location": location},
                confidence=0.88,
                response="Let me look that up online.",
            )

        # Fallback (should not be reached)
        return ReasoningResult(
            action=ActionType.UNSUPPORTED,
            parameters={},
            confidence=1.0,
            response="I cannot answer this reliably using my current local capabilities.",
        )
