"""The audio of the mentor.

The team has a small budget for the speech synthesis, so every answer is
cached on disk: the same sentence in the same voice is only paid for once.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from app.integration.ai.elevenlabs import TTSProvider
from app.logging_config import get_logger

logger = get_logger(__name__)

#: Below this size the file is considered broken and is synthesised again.
_MINIMUM_AUDIO_BYTES = 256


@dataclass
class AudioResult:
    """The audio of an answer and where it is served from."""

    audio: bytes
    filename: str
    cached: bool

    @property
    def url_path(self) -> str:
        """The path the audio is served under."""
        return f"/audio/{self.filename}"


class TtsService:
    """Turns the text of the mentor into audio, with a cache."""

    def __init__(self, provider: TTSProvider, cache_dir: Path) -> None:
        self._provider = provider
        self._cache_dir = Path(cache_dir)

    def _cache_path(self, voice: str, text: str) -> Path:
        digest = hashlib.sha256(f"{voice}::{text.strip()}".encode()).hexdigest()[:12]
        return self._cache_dir / f"tts_{digest}.mp3"

    async def synthesize(self, text: str, voice_profile: dict[str, str]) -> AudioResult:
        """The audio of the text, in the voice of the household."""
        voice = voice_profile.get("voice_id") or voice_profile.get("fallback_voice") or ""
        if not voice:
            return AudioResult(audio=b"", filename="", cached=False)

        path = self._cache_path(voice, text)
        if path.is_file() and path.stat().st_size > _MINIMUM_AUDIO_BYTES:
            return AudioResult(
                audio=path.read_bytes(), filename=path.name, cached=True
            )

        self._cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            audio = await self._provider.synthesize(text, voice)
        except Exception as exc:  # noqa: BLE001 - the text still reaches the client
            logger.warning("The speech synthesis failed: %s", type(exc).__name__)
            try:
                audio = await self._provider.synthesize(
                    text, voice_profile.get("fallback_voice", voice)
                )
            except Exception:  # noqa: BLE001
                return AudioResult(audio=b"", filename="", cached=False)

        if audio and len(audio) > _MINIMUM_AUDIO_BYTES:
            path.write_bytes(audio)
        return AudioResult(audio=audio, filename=path.name, cached=False)

    def cached_files(self) -> list[Path]:
        """The audio files in the cache."""
        if not self._cache_dir.is_dir():
            return []
        return sorted(self._cache_dir.glob("tts_*.mp3"))
