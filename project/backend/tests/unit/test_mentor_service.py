"""The mentor: the conversation, the speech and the cache."""

from __future__ import annotations

import asyncio

import pytest

from app.integration.ai.ai_service import AIService
from app.integration.ai.fake import FakeProvider
from app.integration.mcp.context import CaseContext
from app.schemas.ai import ChatResponse, ToolCall
from app.services.mentor_service import MentorService
from app.services.tts_service import TtsService


class FakeTts:
    """A speech provider that counts its calls."""

    name = "fake"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def synthesize(self, text: str, voice: str) -> bytes:
        self.calls.append((text, voice))
        return b"ID3" + b"x" * 400


def _tool_turn() -> ChatResponse:
    return ChatResponse(
        content="",
        tool_calls=[
            ToolCall(
                id="call_1",
                name="get_case",
                arguments={"part": "financial-health", "section": "score"},
            )
        ],
        model="fake",
    )


def _answer(text: str = "Esa tarjeta te cuesta 3.240 al año.") -> ChatResponse:
    return ChatResponse(content=text, model="fake")


@pytest.fixture()
def context(case_source):
    return CaseContext(case_source)


def test_the_mentor_answers_with_the_plan(context):
    provider = FakeProvider(chat_answers=[_tool_turn(), _answer()])
    service = AIService(provider, model="fake-model")
    mentor = MentorService(service, context, with_audio=False)

    answer = asyncio.run(
        mentor.ask(case_id="timothy-melanie-weah", question="¿Cuánto me cuesta la tarjeta?")
    )

    assert answer.text == "Esa tarjeta te cuesta 3.240 al año."
    assert answer.mcp_used is True
    assert answer.consulted == ["financial-health.score"]


def test_the_mentor_uses_the_register_of_the_household(context):
    provider = FakeProvider(chat_answers=[_answer()])
    service = AIService(provider, model="fake-model")
    mentor = MentorService(service, context, with_audio=False)

    answer = asyncio.run(
        mentor.ask(case_id="samantha-lewis", question="¿Hola?")
    )
    assert answer.voice_profile["style_key"] == "formal"

    answer = asyncio.run(mentor.ask(case_id="weah", question="¿Hola?"))
    assert answer.voice_profile["style_key"] == "refranero"


def test_the_household_can_ask_for_another_register(context):
    provider = FakeProvider(chat_answers=[_answer()])
    service = AIService(provider, model="fake-model")
    mentor = MentorService(service, context, with_audio=False)

    answer = asyncio.run(
        mentor.ask(case_id="weah", question="Hola", style="formal")
    )
    assert answer.voice_profile["style_key"] == "formal"


def test_the_brief_of_the_household_reaches_the_model(context):
    provider = FakeProvider(chat_answers=[_answer()])
    service = AIService(provider, model="fake-model")
    mentor = MentorService(service, context, with_audio=False)

    asyncio.run(mentor.ask(case_id="timothy-melanie-weah", question="Hola"))
    system = provider.chat_calls[0]["messages"][0]["content"]
    assert "CHULETA INTERNA" in system
    assert "Timothy" in system
    assert "REGLA DE ORO" in system


def test_the_mentor_answers_with_audio(context, tmp_path):
    provider = FakeProvider(chat_answers=[_answer()])
    service = AIService(provider, model="fake-model")
    tts = FakeTts()
    mentor = MentorService(service, context, TtsService(tts, tmp_path))

    answer = asyncio.run(mentor.ask(case_id="weah", question="Hola"))

    assert answer.audio_url and answer.audio_url.startswith("/audio/")
    assert tts.calls
    assert answer.audio_cached is False


def test_the_audio_is_cached(context, tmp_path):
    provider = FakeProvider(chat_answers=[_answer(), _answer()])
    service = AIService(provider, model="fake-model")
    tts = FakeTts()
    mentor = MentorService(service, context, TtsService(tts, tmp_path))

    asyncio.run(mentor.ask(case_id="weah", question="Hola"))
    second = asyncio.run(mentor.ask(case_id="weah", question="Hola"))

    assert len(tts.calls) == 1
    assert second.audio_cached is True
    assert second.audio_url


def test_the_mentor_survives_a_broken_tool(context):
    provider = FakeProvider(chat_answers=[_tool_turn(), _answer("Lo siento.")])
    service = AIService(provider, model="fake-model")
    mentor = MentorService(service, context, with_audio=False)

    original = context.get_section

    async def failing(case_id, part, section=None, sub_section=None, compact_for_llm=False):
        if compact_for_llm:
            raise RuntimeError("the plan is not available")
        return await original(case_id, part, section, sub_section, compact_for_llm)

    context.get_section = failing  # type: ignore[method-assign]
    answer = asyncio.run(mentor.ask(case_id="weah", question="Hola"))
    assert answer.text == "Lo siento."
    assert answer.consulted == []
