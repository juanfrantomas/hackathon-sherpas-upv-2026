"""The chat side of the provider: a conversation with tools."""

from __future__ import annotations

import asyncio
import json

import pytest

from app.integration.ai.ai_service import AIService
from app.integration.ai.fake import FakeProvider
from app.schemas.ai import ChatResponse, ToolCall


def _tool_turn(call_id: str = "call_1", name: str = "get_case") -> ChatResponse:
    return ChatResponse(
        content="",
        tool_calls=[
            ToolCall(id=call_id, name=name, arguments={"part": "financial-health"})
        ],
        model="fake",
    )


def _answer(text: str = "Here is the answer.") -> ChatResponse:
    return ChatResponse(content=text, model="fake")


def test_the_tool_is_called_and_the_answer_returned():
    provider = FakeProvider(chat_answers=[_tool_turn(), _answer("The card is at 18%.")])
    service = AIService(provider, model="fake-model")
    asked: list[tuple[str, dict]] = []

    async def handler(name: str, arguments: dict) -> str:
        asked.append((name, arguments))
        return json.dumps({"score": 60})

    outcome = asyncio.run(
        service.chat_with_tools(
            messages=[{"role": "user", "content": "What is my score?"}],
            tools=[{"type": "function", "function": {"name": "get_case"}}],
            tool_handler=handler,
        )
    )

    assert outcome.content == "The card is at 18%."
    assert outcome.tools_used == ["get_case"]
    assert asked == [("get_case", {"part": "financial-health"})]


def test_a_model_that_asks_for_no_tool_answers_at_once():
    provider = FakeProvider(chat_answers=[_answer("Just this.")])
    service = AIService(provider, model="fake-model")

    async def handler(name: str, arguments: dict) -> str:  # pragma: no cover
        raise AssertionError("the tool must not be called")

    outcome = asyncio.run(
        service.chat_with_tools(
            messages=[{"role": "user", "content": "Hello"}],
            tool_handler=handler,
        )
    )

    assert outcome.content == "Just this."
    assert outcome.tools_used == []
    assert outcome.turns == 1


def test_the_tool_result_is_appended_to_the_conversation():
    provider = FakeProvider(chat_answers=[_tool_turn(), _answer()])
    service = AIService(provider, model="fake-model")

    async def handler(name: str, arguments: dict) -> str:
        return '{"value": 60}'

    asyncio.run(
        service.chat_with_tools(
            messages=[{"role": "user", "content": "Score?"}],
            tools=[{"type": "function", "function": {"name": "get_case"}}],
            tool_handler=handler,
        )
    )

    second_call = provider.chat_calls[1]["messages"]
    roles = [message["role"] for message in second_call]
    assert roles == ["user", "assistant", "tool"]
    assert second_call[-1]["content"] == '{"value": 60}'


def test_the_loop_stops_after_the_maximum_number_of_turns():
    provider = FakeProvider(chat_answers=[_tool_turn()] * 5)
    service = AIService(provider, model="fake-model")

    async def handler(name: str, arguments: dict) -> str:
        return "{}"

    outcome = asyncio.run(
        service.chat_with_tools(
            messages=[{"role": "user", "content": "Loop"}],
            tools=[{"type": "function", "function": {"name": "get_case"}}],
            tool_handler=handler,
            max_turns=3,
        )
    )

    assert len(provider.chat_calls) == 3
    assert outcome.turns == 4


def test_the_assistant_message_keeps_the_tool_calls():
    response = _tool_turn()
    message = response.to_assistant_message()
    assert message["role"] == "assistant"
    assert message["tool_calls"][0]["id"] == "call_1"
    assert message["tool_calls"][0]["function"]["name"] == "get_case"
    assert json.loads(message["tool_calls"][0]["function"]["arguments"]) == {
        "part": "financial-health"
    }


def test_a_tool_call_with_broken_arguments_is_read_as_empty():
    call = ToolCall.from_payload(
        {"id": "x", "function": {"name": "get_case", "arguments": "{not json"}}
    )
    assert call.arguments == {}


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"part": "persona"}, {"part": "persona"}),
        ("{}", {}),
    ],
)
def test_the_arguments_are_parsed(payload, expected):
    call = ToolCall.from_payload(
        {"id": "x", "function": {"name": "get_case", "arguments": payload}}
    )
    assert call.arguments == expected
