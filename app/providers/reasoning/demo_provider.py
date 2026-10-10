from __future__ import annotations

import re

from app.domain.interfaces import ReasoningProvider
from app.domain.models import ActionType, ReasoningResult
from app.providers.reasoning.local_answers import local_answer


class DemoReasoningProvider(ReasoningProvider):
    """Deterministic keyword-based reasoning provider for demo/offline mode."""

    # Ordered list of (action, keywords, needs_extraction) tuples.
    # Order matters: more specific patterns are checked first.
    _RULES: list[tuple[ActionType, list[str]]] = [
        (ActionType.LIST_TASKS, [
            "show tasks", "list tasks", "pending tasks", "my tasks",
        ]),
        (ActionType.COMPLETE_TASK, [
            "mark", "complete", "finish", "done with",
        ]),
        (ActionType.ADD_TASK, [
            "add to my task list", "add to task", "create task", "new task", "add task",
        ]),
        (ActionType.SAVE_MEMORY, [
            "keep in mind", "note that", "remember", "save", "store",
            "birthday is", "meeting is", "deadline is", "password is",
            "email is", "phone number is", "address is", "anniversary is",
        ]),
        (ActionType.NEWS_LOOKUP, [
            "news", "headlines", "latest news", "what's happening",
        ]),
        (ActionType.WEATHER_LOOKUP, [
            "weather", "temperature", "forecast",
        ]),
        (ActionType.SEARCH_MEMORY, [
            "do you remember", "what do you know about",
            "recall", "find", "search",
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
        direct = local_answer(text)
        if direct is not None:
            return direct
        lower = text.lower().strip()

        for keyword in ("do you remember", "what do you know about"):
            if lower.startswith(keyword):
                return self._build_result(ActionType.SEARCH_MEMORY, text, lower, keyword)

        for keyword in ("keep in mind", "note that", "remember", "save", "store"):
            if re.match(rf"^{re.escape(keyword)}\b", lower):
                return self._build_result(ActionType.SAVE_MEMORY, text, lower, keyword)

        for action, keywords in self._RULES:
            # Sort keywords longest-first so the most specific phrase wins.
            for kw in sorted(keywords, key=len, reverse=True):
                if re.search(rf"\b{re.escape(kw)}\b", lower):
                    if action in (ActionType.ADD_TASK, ActionType.COMPLETE_TASK) and not lower.startswith(kw):
                        continue
                    if action == ActionType.SAVE_MEMORY and not re.match(r"^(?:my\s+)?(?:meeting|birthday|deadline|password|email|phone number|address|anniversary)\s+is\b", lower):
                        continue
                    return self._build_result(action, text, lower, kw)

        # Nothing matched -> unsupported
        return ReasoningResult(
            action=ActionType.UNSUPPORTED,
            parameters={},
            confidence=1.0,
            response="Demo mode handles memories, tasks, and simple arithmetic. For general conversation, switch to Local AI mode with a running local model.",
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
            # Strip an explicit instruction, but keep the subject of stated facts.
            content = original.strip()
            if matched_keyword in {"keep in mind", "note that", "remember", "save", "store"}:
                idx = lower.find(matched_keyword) + len(matched_keyword)
                content = re.sub(r"^that\s+", "", original[idx:].strip(), flags=re.I)
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

        if action == ActionType.NEWS_LOOKUP:
            topic = self._extract_after_keyword(lower, matched_keyword)
            return ReasoningResult(
                action=ActionType.NEWS_LOOKUP,
                parameters={"topic": topic},
                confidence=0.88,
                response="Let me fetch the latest headlines.",
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
