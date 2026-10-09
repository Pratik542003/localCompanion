from __future__ import annotations

import json
import logging

import httpx

from app.domain.interfaces import ReasoningProvider
from app.domain.models import ActionType, ReasoningResult

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a local AI assistant that classifies user commands. Respond ONLY with valid JSON.
Classify the user input into exactly one of these actions:
- save_memory: User wants to save/remember information. Extract the content to save.
- search_memory: User wants to find/recall saved information. Extract the search query.
- add_task: User wants to add a task. Extract the task title.
- list_tasks: User wants to see their tasks.
- complete_task: User wants to mark a task done. Extract the task title.
- weather_lookup: User wants weather info. Extract the location.
- unsupported: Request cannot be handled locally.

Respond with this exact JSON structure:
{"action": "<action_type>", "parameters": {...}, "confidence": <0.0-1.0>, "response": "<brief response>"}"""


class LlamaCppReasoningProvider(ReasoningProvider):
    """Reasoning provider backed by a local llama.cpp server."""

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: int,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    async def reason(self, text: str) -> ReasoningResult:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "temperature": 0.1,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
            )
            resp.raise_for_status()

        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # The model might wrap its JSON in markdown fences; strip them.
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        parsed = json.loads(content)
        return ReasoningResult(
            action=ActionType(parsed["action"]),
            parameters=parsed.get("parameters", {}),
            confidence=float(parsed.get("confidence", 0.5)),
            response=parsed.get("response", ""),
        )

    def is_available(self) -> bool:
        """Synchronous availability check against the llama.cpp server."""
        try:
            resp = httpx.get(
                f"{self._base_url}/v1/models",
                timeout=3,
            )
            return resp.is_success
        except (httpx.HTTPError, OSError):
            pass

        try:
            resp = httpx.get(
                f"{self._base_url}/health",
                timeout=3,
            )
            return resp.is_success
        except (httpx.HTTPError, OSError):
            return False

    def provider_name(self) -> str:
        return "llama_cpp"
