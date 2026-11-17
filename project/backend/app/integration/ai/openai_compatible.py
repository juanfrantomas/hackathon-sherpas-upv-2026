"""Adapter for OpenAI compatible providers.

The Sherpas hackathon proxy (``https://llm-hackathon.sherpaswealth.com/v1``)
speaks the OpenAI chat completions protocol and supports structured output
with ``response_format={"type": "json_schema", ...}``.  Any other provider
that speaks the same protocol works too.
"""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from typing import Any

import httpx

from app.integration.ai.errors import (
    AiAuthError,
    AiProviderUnavailableError,
    AiResponseTooLargeError,
)
from app.integration.ai.provider import AIResponse
from app.logging_config import get_logger
from app.schemas.ai import ChatResponse, ToolCall

logger = get_logger(__name__)

_RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


class OpenAICompatibleProvider:
    """Calls an OpenAI compatible ``/chat/completions`` endpoint."""

    name = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 90.0,
        max_retries: int = 3,
        max_concurrency: int = 4,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries
        self._semaphore = asyncio.Semaphore(max(1, max_concurrency))
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any],
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> AIResponse:
        """Ask the provider for JSON matching ``schema``."""
        if not self._api_key:
            raise AiAuthError("No AI credentials are configured")

        payload: dict[str, Any] = {
            "model": model or self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": _as_json_schema(schema),
            },
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with self._semaphore:
            data = await self._post(payload)
        return _parse_response(data)

    async def chat(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> ChatResponse:
        """A free conversation, optionally with tools the model may call."""
        if not self._api_key:
            raise AiAuthError("No AI credentials are configured")

        payload: dict[str, Any] = {
            "model": model or self._model,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice or "auto"
        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with self._semaphore:
            data = await self._post(payload)
        return _parse_chat(data)

    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        client = await self._get_client()
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                response = await client.post(url, json=payload, headers=headers)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                logger.warning("AI provider request failed (attempt %s): %s", attempt, type(exc).__name__)
                await self._backoff(attempt)
                continue

            if response.status_code == 401 or response.status_code == 403:
                raise AiAuthError("The AI provider rejected our credentials")
            if response.status_code in _RETRY_STATUS:
                last_error = AiProviderUnavailableError(
                    f"The AI provider answered with status {response.status_code}"
                )
                logger.warning(
                    "AI provider busy (%s), retrying (attempt %s)",
                    response.status_code,
                    attempt,
                )
                await self._backoff(attempt)
                continue
            if response.status_code >= 400:
                raise AiProviderUnavailableError(
                    f"The AI provider answered with status {response.status_code}"
                )
            try:
                return response.json()
            except json.JSONDecodeError as exc:
                raise AiProviderUnavailableError(
                    "The AI provider answered with a payload that is not JSON"
                ) from exc

        raise AiProviderUnavailableError(
            f"The AI provider is unavailable after {self._max_retries} attempts"
        ) from last_error

    async def _backoff(self, attempt: int) -> None:
        delay = min(2 ** attempt, 20)
        await asyncio.sleep(delay)


def _as_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """The schema in the shape the provider expects.

    A bare JSON schema is wrapped with a name and the strict flag; a schema
    that already carries them is used as it is.
    """
    if "schema" in schema and "name" in schema:
        return schema
    return {
        "name": str(schema.get("name") or "response"),
        "strict": True,
        "schema": {key: value for key, value in schema.items() if key != "name"},
    }


def _parse_chat(data: dict[str, Any]) -> ChatResponse:
    """Build a chat answer from the payload of the provider."""
    choices = data.get("choices") or []
    if not choices:
        raise AiResponseTooLargeError("The AI provider returned no choices")
    choice = choices[0]
    message = choice.get("message") or {}

    tool_calls = [
        ToolCall.from_payload(call)
        for call in (message.get("tool_calls") or [])
        if isinstance(call, dict)
    ]
    usage = data.get("usage") or {}
    cost = usage.get("cost")
    return ChatResponse(
        content=str(message.get("content") or "").strip(),
        tool_calls=tool_calls,
        model=str(data.get("model") or ""),
        input_tokens=usage.get("prompt_tokens"),
        output_tokens=usage.get("completion_tokens"),
        cost_usd=Decimal(str(cost)) if cost is not None else None,
        finish_reason=choice.get("finish_reason"),
    )


def _parse_response(data: dict[str, Any]) -> AIResponse:
    choices = data.get("choices") or []
    if not choices:
        raise AiResponseTooLargeError("The AI provider returned no choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise AiResponseTooLargeError(
            "The AI provider returned an empty answer; raise max_tokens"
        )

    usage = data.get("usage") or {}
    cost = usage.get("cost")
    return AIResponse(
        content=content,
        model=str(data.get("model") or ""),
        input_tokens=usage.get("prompt_tokens"),
        output_tokens=usage.get("completion_tokens"),
        cost_usd=Decimal(str(cost)) if cost is not None else None,
        raw={"id": data.get("id"), "finish_reason": choices[0].get("finish_reason")},
    )
