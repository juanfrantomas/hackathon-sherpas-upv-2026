"""The realtime voice session.

The proxy of the hackathon speaks the realtime protocol over a WebSocket: the
browser sends audio to the backend, the backend relays it to the proxy and
relays the answer back.  The protocol lives here; the session itself lives in
:mod:`app.realtime.handler`.
"""

from __future__ import annotations

import json
import ssl
from dataclasses import dataclass
from typing import Any

from app.logging_config import get_logger

logger = get_logger(__name__)

#: The models the proxy offers for the voice.
DEFAULT_REALTIME_MODELS = ("gpt-realtime-2.1-mini", "gpt-realtime-2.1", "gemini-3.8-live")

#: The rate of the PCM audio the protocol uses.
AUDIO_SAMPLE_RATE = 24000


def realtime_url(base_url: str, model: str) -> str:
    """The address of the realtime session of a model."""
    url = base_url.rstrip("/")
    if url.endswith("/v1"):
        url = url[: -len("/v1")]
    url = url.replace("https://", "wss://").replace("http://", "ws://")
    return f"{url}/v1/realtime?model={model}"


@dataclass
class AudioConfig:
    """The audio format of a realtime session."""

    voice: str
    transcription_model: str | None = None

    def to_payload(self) -> dict[str, Any]:
        """The ``audio`` block of the session."""
        audio: dict[str, Any] = {
            "input": {
                "format": {"type": "audio/pcm", "rate": AUDIO_SAMPLE_RATE},
                "turn_detection": {"type": "server_vad", "silence_duration_ms": 500},
            },
            "output": {
                "format": {"type": "audio/pcm", "rate": AUDIO_SAMPLE_RATE},
                "voice": self.voice,
            },
        }
        if self.transcription_model:
            audio["input"]["transcription"] = {"model": self.transcription_model}
        return audio


class RealtimeProxy:
    """The connection to the realtime model of the proxy."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        model: str,
        ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        self._url = realtime_url(base_url, model)
        self._token = token
        self._model = model
        self._ssl = ssl_context
        self._connection: Any = None

    async def __aenter__(self) -> RealtimeProxy:
        await self.connect()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    async def connect(self) -> None:
        """Open the connection to the proxy."""
        import websockets

        headers = {"Authorization": f"Bearer {self._token}"}
        context = self._ssl
        if context is None and self._url.startswith("wss://"):
            # A secure session needs a trust store.
            import certifi

            context = ssl.create_default_context(cafile=certifi.where())
        self._connection = await websockets.connect(
            self._url, additional_headers=headers, ssl=context
        )
        logger.info("Realtime session opened for %s", self._model)

    async def send(self, payload: dict[str, Any] | str) -> None:
        """Send a message to the proxy."""
        if self._connection is None:  # pragma: no cover - defensive
            raise RuntimeError("The realtime session is not open")
        data = payload if isinstance(payload, str) else json.dumps(payload)
        await self._connection.send(data)

    async def receive(self) -> str:
        """Wait for the next message of the proxy."""
        if self._connection is None:  # pragma: no cover - defensive
            raise RuntimeError("The realtime session is not open")
        return await self._connection.recv()

    async def close(self) -> None:
        """Close the connection."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
