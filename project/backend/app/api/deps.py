"""FastAPI dependencies."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.config import BASE_DIR, Settings, get_settings
from app.errors import CaseNotAllowedError
from app.integration.ai.ai_service import AIService
from app.integration.ai.elevenlabs import OpenAICompatibleTTS, TTSProvider
from app.integration.ai.fake import FakeProvider
from app.integration.ai.openai_compatible import OpenAICompatibleProvider
from app.integration.ai.provider import AIProvider
from app.integration.mcp.case_source import (
    AutoCaseSource,
    CaseSource,
    LocalCaseSource,
    McpCaseSource,
)
from app.integration.mcp.client import McpClient
from app.integration.mcp.context import CaseContext
from app.services.mentor_service import MentorService
from app.services.tts_service import TtsService


def settings_dependency() -> Settings:
    """The application settings."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(settings_dependency)]


@lru_cache(maxsize=4)
def _build_case_source(
    case_source: str, cases_dir: str, digest_max_chars: int, mcp_url: str, mcp_token: str
) -> CaseSource:
    """Build the case source once per configuration."""
    local = LocalCaseSource(Path(cases_dir), max_chars=digest_max_chars)
    if case_source == "local":
        return local
    client = McpClient(mcp_url, mcp_token)
    mcp = McpCaseSource(client, max_chars=digest_max_chars)
    if case_source == "mcp":
        return mcp
    return AutoCaseSource(mcp, local)


def case_source_dependency(settings: SettingsDep) -> CaseSource:
    """The configured case source."""
    return _build_case_source(
        settings.case_source,
        settings.resolved_cases_dir.as_posix(),
        settings.digest_max_chars,
        settings.mcp_url,
        settings.mcp_token,
    )


CaseSourceDep = Annotated[CaseSource, Depends(case_source_dependency)]


@lru_cache(maxsize=4)
def _build_provider(
    ai_provider: str, base_url: str, api_key: str, model: str, timeout: float, retries: int, concurrency: int
) -> AIProvider:
    if ai_provider == "fake":
        return FakeProvider()
    return OpenAICompatibleProvider(
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout=timeout,
        max_retries=retries,
        max_concurrency=concurrency,
    )


def ai_service_dependency(settings: SettingsDep) -> AIService:
    """The AI service used to generate milestones."""
    provider = _build_provider(
        settings.ai_provider,
        settings.ai_base_url,
        settings.ai_api_key,
        settings.ai_model,
        float(settings.ai_timeout_s),
        settings.ai_max_retries,
        settings.ai_max_concurrency,
    )
    return AIService(
        provider,
        model=settings.ai_model,
        max_output_tokens=settings.ai_max_output_tokens,
    )


def case_context_dependency(
    settings: SettingsDep, case_source: CaseSourceDep
) -> CaseContext:
    """The reader of the plan for the conversations."""
    return CaseContext(case_source)


CaseContextDep = Annotated[CaseContext, Depends(case_context_dependency)]


@lru_cache(maxsize=2)
def _build_tts_provider(
    base_url: str, api_key: str, model: str
) -> TTSProvider:
    return OpenAICompatibleTTS(base_url=base_url, api_key=api_key, model=model)


def tts_service_dependency(settings: SettingsDep) -> TtsService:
    """The speech of the mentor, with its cache."""
    provider = _build_tts_provider(
        settings.ai_base_url, settings.ai_api_key, settings.tts_model
    )
    cache_dir = Path(settings.tts_cache_dir)
    if not cache_dir.is_absolute():
        cache_dir = (BASE_DIR / cache_dir).resolve()
    return TtsService(provider, cache_dir)


TTSServiceDep = Annotated[TtsService, Depends(tts_service_dependency)]


def mentor_service_dependency(
    settings: SettingsDep,
    ai_service: AIServiceDep,
    context: CaseContextDep,
    tts_service: TTSServiceDep,
) -> MentorService:
    """The mentor of the households."""
    return MentorService(
        ai_service,
        context,
        tts_service if settings.tts_enabled else None,
        model=settings.mentor_model,
        max_tokens=settings.mentor_max_tokens,
        with_audio=settings.mentor_with_audio,
    )


MentorServiceDep = Annotated[MentorService, Depends(mentor_service_dependency)]


AIServiceDep = Annotated[AIService, Depends(ai_service_dependency)]


def authorize_case(case_id: str, settings: Settings) -> str:
    """Check that this instance may serve the requested case.

    The allowlist is a guard rail for the prototype, not an authentication
    mechanism.  An empty allowlist denies everything.

    Returns the official slug of the case, so the caller works with it.
    """
    from app.services.case_service import normalize_case_id

    slug = normalize_case_id(case_id)
    allowed = settings.allowed_case_id_set
    if not allowed:
        raise CaseNotAllowedError(
            "This instance does not serve any case",
            details={"case_id": slug},
        )
    if slug not in allowed:
        raise CaseNotAllowedError(
            "This case is not served by this instance",
            details={"case_id": slug},
        )
    return slug


def reset_dependencies() -> None:
    """Drop the cached providers (used by the test suite)."""
    _build_case_source.cache_clear()
    _build_provider.cache_clear()


__all__ = [
    "AIServiceDep",
    "CaseSourceDep",
    "SettingsDep",
    "HTTPException",
    "status",
    "authorize_case",
    "ai_service_dependency",
    "case_source_dependency",
    "reset_dependencies",
]
