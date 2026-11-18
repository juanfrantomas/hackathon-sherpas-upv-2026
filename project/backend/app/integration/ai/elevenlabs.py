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
        import os
        import httpx

        eleven_key = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
        if eleven_key:
            try:
                limits = httpx.Limits(max_keepalive_connections=0, max_connections=10)
                async with httpx.AsyncClient(limits=limits, timeout=httpx.Timeout(12.0, connect=3.0)) as http_client:
                    res = await http_client.post(
                        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                        headers={
                            "xi-api-key": eleven_key,
                            "Content-Type": "application/json",
                            "Accept": "audio/mpeg",
                            "Connection": "close",
                        },
                        json={
                            "text": text,
                            "model_id": "eleven_multilingual_v2",
                            "voice_settings": {
                                "stability": 0.48,
                                "similarity_boost": 0.78,
                                "style": 0.20,
                                "use_speaker_boost": True,
                                "speed": 1.0,
                            },
                        },
                    )
                    if res.status_code == 200 and len(res.content) > 500:
                        return res.content
            except Exception:
                pass

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
