"""The data exchanged with a chat provider.

The provider speaks the OpenAI protocol on the wire; these types are what the
application works with, so no vendor detail leaks into the services.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class ToolCall:
    """A tool the model wants to call."""

    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> ToolCall:
        """Build a tool call from the payload of a provider."""
        function = payload.get("function") or {}
        raw_arguments = function.get("arguments") or "{}"
        try:
            arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else dict(raw_arguments)
        except json.JSONDecodeError:
            arguments = {}
        return cls(
            id=str(payload.get("id") or ""),
            name=str(function.get("name") or ""),
            arguments=arguments,
        )


@dataclass
class ChatResponse:
    """What a provider answered to a chat turn."""

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: Decimal | None = None
    finish_reason: str | None = None

    @property
    def wants_tools(self) -> bool:
        """Whether the model asked for a tool."""
        return bool(self.tool_calls)

    def to_assistant_message(self) -> dict[str, Any]:
        """The assistant turn, ready to be appended to the conversation."""
        message: dict[str, Any] = {"role": "assistant", "content": self.content or None}
        if self.tool_calls:
            message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments, ensure_ascii=False),
                    },
                }
                for call in self.tool_calls
            ]
        return message
