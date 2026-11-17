"""The live voice session."""

from __future__ import annotations

import asyncio
import json

import pytest

from app.integration.ai.realtime import AudioConfig, realtime_url
from app.integration.mcp.context import CaseContext
from app.realtime import handler as realtime_handler
from app.realtime.handler import compose_instructions


class FakeWebSocket:
    """A websocket that plays the part of the browser."""

    def __init__(self, incoming: list[str] | None = None) -> None:
        self.incoming = list(incoming or [])
        self.sent_json: list[dict] = []
        self.sent_text: list[str] = []
        self.accepted = False
        self.closed = False

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, payload: dict) -> None:
        self.sent_json.append(payload)

    async def send_text(self, payload: str) -> None:
        self.sent_text.append(payload)

    async def receive_text(self) -> str:
        if self.incoming:
            return self.incoming.pop(0)
        raise RuntimeError("the browser closed the connection")

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = True


class FakeProxy:
    """The connection to the proxy, recorded."""

    instances: list[FakeProxy] = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.sent: list[dict | str] = []
        self.received: list[str] = []
        self.closed = False
        FakeProxy.instances.append(self)

    async def connect(self) -> None:
        return None

    async def send(self, payload) -> None:
        self.sent.append(payload)

    async def receive(self) -> str:
        if self.received:
            return self.received.pop(0)
        await asyncio.sleep(0.01)
        raise RuntimeError("the proxy closed the connection")

    async def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def fake_proxy(monkeypatch):
    FakeProxy.instances = []
    monkeypatch.setattr(realtime_handler, "RealtimeProxy", FakeProxy)
    return FakeProxy


@pytest.fixture()
def context(case_source):
    return CaseContext(case_source)


def _run(coro):
    return asyncio.run(coro)


def test_the_address_of_the_realtime_session():
    assert (
        realtime_url("https://llm-hackathon.sherpaswealth.com/v1", "gemini-3.8-live")
        == "wss://llm-hackathon.sherpaswealth.com/v1/realtime?model=gemini-3.8-live"
    )


def test_the_audio_configuration():
    config = AudioConfig(voice="Aoede").to_payload()
    assert config["input"]["format"] == {"type": "audio/pcm", "rate": 24000}
    assert config["output"]["voice"] == "Aoede"
    assert "transcription" not in config["input"]

    with_transcription = AudioConfig(
        voice="coral", transcription_model="gpt-4o-mini-transcribe"
    ).to_payload()
    assert with_transcription["input"]["transcription"]["model"] == "gpt-4o-mini-transcribe"


def test_the_instructions_hold_the_register_and_the_brief():
    profile = {
        "tone_instructions": "REGISTRO: CERCANO",
        "style_key": "refranero",
    }
    instructions = compose_instructions(profile, "CHULETA", include_tools=False)
    assert "REGISTRO: CERCANO" in instructions
    assert "CHULETA" in instructions
    assert "get_case" not in instructions

    with_tools = compose_instructions(profile, "CHULETA", include_tools=True)
    assert "get_case" in with_tools


def test_the_session_opens_and_announces_itself(context):
    websocket = FakeWebSocket()

    _run(
        realtime_handler.handle_realtime_websocket(
            websocket,
            "timothy-melanie-weah",
            context=context,
            proxy_base_url="https://proxy.invalid/v1",
            token="secret",
            model="gemini-3.8-live",
        )
    )

    assert websocket.accepted is True
    ready = websocket.sent_json[0]
    assert ready["type"] == "session_ready"
    assert ready["case_id"] == "timothy-melanie-weah"
    assert ready["style_key"] == "refranero"
    assert ready["is_couple"] is True
    assert ready["voice"] == "Aoede"


def test_the_session_updates_the_proxy(context):
    websocket = FakeWebSocket()

    _run(
        realtime_handler.handle_realtime_websocket(
            websocket,
            "weah",
            context=context,
            proxy_base_url="https://proxy.invalid/v1",
            token="secret",
            model="gpt-realtime-2.1-mini",
        )
    )

    proxy = FakeProxy.instances[0]
    update = proxy.sent[0]
    assert update["type"] == "session.update"
    assert update["session"]["audio"]["output"]["voice"] == "coral"
    assert update["session"]["tools"][0]["name"] == "get_case"


def test_the_audio_is_relayed_without_being_parsed(context):
    packet = json.dumps({"type": "input_audio_buffer.append", "audio": "AAAA"})
    websocket = FakeWebSocket([packet])

    _run(
        realtime_handler.handle_realtime_websocket(
            websocket,
            "weah",
            context=context,
            proxy_base_url="https://proxy.invalid/v1",
            token="secret",
        )
    )

    proxy = FakeProxy.instances[0]
    assert packet in proxy.sent


def test_the_text_of_the_household_reaches_the_proxy(context):
    websocket = FakeWebSocket([json.dumps({"type": "user_text", "text": "Hola"})])

    _run(
        realtime_handler.handle_realtime_websocket(
            websocket,
            "weah",
            context=context,
            proxy_base_url="https://proxy.invalid/v1",
            token="secret",
        )
    )

    proxy = FakeProxy.instances[0]
    creations = [
        payload
        for payload in proxy.sent
        if isinstance(payload, dict)
        and payload.get("type") == "conversation.item.create"
    ]
    assert creations
    assert creations[0]["item"]["content"][0]["text"] == "Hola"


def test_the_greeting_of_a_milestone(context):
    websocket = FakeWebSocket()

    _run(
        realtime_handler.handle_realtime_websocket(
            websocket,
            "weah",
            context=context,
            proxy_base_url="https://proxy.invalid/v1",
            token="secret",
            topic="la tarjeta de crédito",
            auto_greet=True,
        )
    )

    proxy = FakeProxy.instances[0]
    creations = [
        payload
        for payload in proxy.sent
        if isinstance(payload, dict)
        and payload.get("type") == "conversation.item.create"
    ]
    assert creations
    assert "la tarjeta de crédito" in creations[0]["item"]["content"][0]["text"]
