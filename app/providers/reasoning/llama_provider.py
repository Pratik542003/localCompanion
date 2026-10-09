from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import httpx

from app.domain.interfaces import ReasoningProvider
from app.domain.models import ActionType, ReasoningResult

logger = logging.getLogger(__name__)

_PROMPT_FILE = Path(__file__).resolve().parent / "system_prompt.txt"

_DEFAULT_PROMPT = """\
Classify the user command. Reply ONLY with valid JSON.

Actions:
- save_memory: User states a FACT to remember (birthday, password, date, name, phone, event).
- search_memory: User asks to recall saved info.
- add_task: User wants to DO something (buy, fix, review, send, prepare).
- list_tasks: User wants to see tasks.
- complete_task: User marks a task done.
- weather_lookup: User asks about weather.
- news_lookup: User asks for news/headlines.
- unsupported: Cannot handle locally.

Rule: A FACT (birthday, password, date) = save_memory. An ACTION to do = add_task.

Examples:
"Shreyash birthday is 25th January" -> save_memory, content="Shreyash birthday is 25th January"
"buy groceries" -> add_task, title="buy groceries"
"when is Shreyash birthday" -> search_memory, query="Shreyash birthday"
"weather in Mumbai" -> weather_lookup, location="Mumbai"
"latest news" -> news_lookup, topic=""
"mark buy groceries done" -> complete_task, title="buy groceries"

JSON format: {"action":"<type>","parameters":{...},"confidence":0.9,"response":"<short>"}
Parameters: save_memory->content, add_task->title, search_memory->query, complete_task->title, weather_lookup->location, news_lookup->topic."""


def _load_prompt() -> str:
    if _PROMPT_FILE.exists():
        return _PROMPT_FILE.read_text(encoding="utf-8").strip()
    return _DEFAULT_PROMPT


def _build_context(memories: list[str], tasks: list[dict]) -> str:
    parts = []

    if memories:
        items = memories[:3]
        parts.append("SAVED MEMORIES:\n" + "\n".join(f"- {m}" for m in items))

    if tasks:
        pending = [t for t in tasks if t.get("status") == "pending"][:3]
        if pending:
            lines = [f"- {t.get('title', '')}" for t in pending]
            parts.append("PENDING TASKS:\n" + "\n".join(lines))

    if not parts:
        return ""

    return "\n\nCONTEXT:\n" + "\n".join(parts)


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Find first { and its matching } using brace counting
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except (json.JSONDecodeError, ValueError):
                    return None
    return None


_FALLBACK_KEYWORDS: list[tuple[ActionType, list[str]]] = [
    (ActionType.WEATHER_LOOKUP, ["weather", "temperature", "forecast"]),
    (ActionType.NEWS_LOOKUP, ["news", "headlines"]),
    (ActionType.LIST_TASKS, ["show tasks", "list tasks", "my tasks"]),
    (ActionType.COMPLETE_TASK, ["mark", "complete", "done with"]),
    (ActionType.ADD_TASK, ["add task", "add to", "create task"]),
    (ActionType.SAVE_MEMORY, ["remember", "save", "birthday is", "password is", "meeting is"]),
    (ActionType.SEARCH_MEMORY, ["when is", "what is", "recall", "find"]),
]


def _fallback_classify(text: str) -> ReasoningResult:
    lower = text.lower()
    for action, keywords in _FALLBACK_KEYWORDS:
        for kw in keywords:
            if kw in lower:
                params = {}
                if action == ActionType.WEATHER_LOOKUP:
                    m = re.search(r"\bin\s+(.+?)(?:\?|$)", lower)
                    params = {"location": m.group(1).strip().rstrip(".") if m else ""}
                elif action == ActionType.SAVE_MEMORY:
                    params = {"content": text.strip()}
                elif action == ActionType.SEARCH_MEMORY:
                    idx = lower.find(kw)
                    params = {"query": text[idx + len(kw):].strip().strip("?.")}
                elif action in (ActionType.ADD_TASK, ActionType.COMPLETE_TASK):
                    idx = lower.find(kw)
                    params = {"title": text[idx + len(kw):].strip().strip(".")}
                elif action == ActionType.NEWS_LOOKUP:
                    params = {"topic": ""}
                return ReasoningResult(
                    action=action, parameters=params,
                    confidence=0.6, response="Processed locally.",
                )
    return ReasoningResult(
        action=ActionType.UNSUPPORTED, parameters={},
        confidence=1.0, response="I cannot answer this reliably using my current local capabilities.",
    )


class LlamaCppReasoningProvider(ReasoningProvider):

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: int,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._memories: list[str] = []
        self._tasks: list[dict] = []

    def set_context(self, memories: list[str], tasks: list[dict]) -> None:
        self._memories = memories
        self._tasks = tasks

    async def reason(self, text: str) -> ReasoningResult:
        base_prompt = _load_prompt()
        context = _build_context(self._memories, self._tasks)
        full_prompt = base_prompt + context

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": full_prompt},
                {"role": "user", "content": text},
            ],
            "temperature": 0.1,
            "max_tokens": 150,
            "stop": ["\n\n"],
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/v1/chat/completions",
                    json=payload,
                )
                resp.raise_for_status()

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("LLM call failed (%s), using fallback classifier", exc)
            return _fallback_classify(text)

        parsed = _extract_json(content)
        if parsed is None:
            logger.warning("LLM returned unparseable content: %s", content[:200])
            return _fallback_classify(text)

        action_str = parsed.get("action", "unsupported")
        try:
            action = ActionType(action_str)
        except ValueError:
            action = ActionType.UNSUPPORTED

        return ReasoningResult(
            action=action,
            parameters=parsed.get("parameters", {}),
            confidence=float(parsed.get("confidence", 0.5)),
            response=parsed.get("response", ""),
        )

    def is_available(self) -> bool:
        try:
            resp = httpx.get(f"{self._base_url}/v1/models", timeout=3)
            return resp.is_success
        except (httpx.HTTPError, OSError):
            pass
        try:
            resp = httpx.get(f"{self._base_url}/health", timeout=3)
            return resp.is_success
        except (httpx.HTTPError, OSError):
            return False

    def provider_name(self) -> str:
        return "llama_cpp"
