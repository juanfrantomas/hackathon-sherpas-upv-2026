"""The provider interface the application depends on.

The domain only ever talks to :class:`AIProvider`.  Swapping the provider is a
matter of implementing this protocol and registering it under a name in
``AI_PROVIDER``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from app.schemas.ai import ChatResponse


@dataclass
class AIResponse:
    """What a provider answered."""

    content: str
    model: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: Decimal | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class AIProvider(Protocol):
    """A text generation provider that can answer with JSON."""

    name: str

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any],
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> AIResponse: ...

    async def chat(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> ChatResponse:
        """A free conversation, optionally with tools the model may call.

        The messages follow the OpenAI protocol: ``{"role": ..., "content": ...}``
        plus the tool turns.
        """
        ...
