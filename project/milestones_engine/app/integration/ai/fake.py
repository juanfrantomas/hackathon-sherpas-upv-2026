"""A deterministic provider used by the tests.

It never calls a network service: it replays a payload that was prepared by
the test (or a sensible default), which keeps the test suite hermetic.
"""

from __future__ import annotations

import json
from typing import Any

from app.integration.ai.errors import AiInvalidResponseError
from app.integration.ai.provider import AIResponse
from app.schemas.ai import ChatResponse


class FakeProvider:
    """Replays a fixed answer."""

    name = "fake"

    def __init__(
        self,
        payload: dict[str, Any] | str | None = None,
        *,
        invalid_once: bool = False,
        chat_answers: list[ChatResponse] | None = None,
    ) -> None:
        self._payload = payload
        self._invalid_once = invalid_once
        self._chat_answers = list(chat_answers or [])
        self.calls: list[dict[str, Any]] = []
        self.chat_calls: list[dict[str, Any]] = []

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any],
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> AIResponse:
        self.calls.append({"system": system, "user": user, "schema": schema})
        if self._invalid_once:
            self._invalid_once = False
            return AIResponse(content="this is not json", model="fake")
        if self._payload is None:
            return AIResponse(content=json.dumps({"milestones": []}), model="fake")
        if isinstance(self._payload, str):
            return AIResponse(content=self._payload, model=model or "fake")
        return AIResponse(
            content=json.dumps(self._payload),
            model=model or "fake",
            input_tokens=123,
            output_tokens=45,
            cost_usd=None,
        )

    async def chat(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> ChatResponse:
        """Replays the prepared answers, one per turn."""
        self.chat_calls.append(
            {"messages": messages, "tools": tools, "tool_choice": tool_choice}
        )
        if self._chat_answers:
            return self._chat_answers.pop(0)
        return ChatResponse(content="", model=model or "fake")


class FailingProvider:
    """A provider that always fails, used to test the degraded paths."""

    name = "failing"

    def __init__(self, error: Exception | None = None) -> None:
        self._error = error or AiInvalidResponseError("nope")

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any],
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> AIResponse:
        raise self._error
