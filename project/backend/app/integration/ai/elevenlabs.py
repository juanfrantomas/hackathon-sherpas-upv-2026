"""Text to speech.

The mentor answers with a voice, not only with words.  The audio is produced
by ElevenLabs through the AI proxy, which speaks the OpenAI protocol for
speech as well.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.logging_config import get_logger

logger = get_logger(__name__)

#: The model that speaks the fastest and the cheapest.
DEFAULT_TTS_MODEL = "eleven-flash-v2.5"


@runtime_checkable
class TTSProvider(Protocol):
    """A provider that turns text into audio."""

    name: str

    async def synthesize(self, text: str, voice: str) -> bytes:
        """The audio of the text, in the voice asked for."""
        ...


class OpenAICompatibleTTS:
    """Speaks through an OpenAI compatible ``/audio/speech`` endpoint."""

    name = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str = DEFAULT_TTS_MODEL,
        client: object | None = None,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._model = model
        self._client = client

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(base_url=self._base_url, api_key=self._api_key)
        return self._client

    async def synthesize(self, text: str, voice: str) -> bytes:
        """The audio of the text."""
        client = self._get_client()
        response = await client.audio.speech.create(
            model=self._model,
            voice=voice,
            input=text,
        )
        content = getattr(response, "content", None)
        if content is None:
            content = await response.read()
        return content
