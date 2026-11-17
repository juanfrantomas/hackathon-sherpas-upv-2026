"""Application configuration.

Every knob is read from the environment (or a local ``.env`` file).  Secrets
are never logged: :func:`app.logging_config.setup_logging` installs a redaction
filter, and this module deliberately keeps the raw values in private
attributes so they do not leak through ``repr()`` of the settings object.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent.parent


class Settings(BaseSettings):
    """Runtime settings for the Financial Milestones module."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- database ---------------------------------------------------------
    database_url: str = "sqlite:///./data/app.db"

    # --- Sherpas MCP ------------------------------------------------------
    mcp_url: str = "https://mcp-hackathon.sherpaswealth.com/mcp"
    mcp_token: str = ""
    case_source: str = "auto"
    cases_dir: str = str(REPO_ROOT / "cases")

    # --- AI ---------------------------------------------------------------
    ai_provider: str = "openai_compatible"
    ai_base_url: str = "https://llm-hackathon.sherpaswealth.com/v1"
    ai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("AI_API_KEY", "TEAM_KEY"),
    )
    ai_model: str = "gpt-5-mini"
    ai_max_concurrency: int = 4
    ai_timeout_s: int = 180
    #: The model that writes the copy of the pillars.  A model without
    #: reasoning keeps the answer short and does not run out of tokens.
    ai_copy_model: str = "gemini-3.5-flash-lite"
    ai_max_retries: int = 3
    ai_max_output_tokens: int = 20000

    # --- digest / generation ----------------------------------------------
    digest_max_chars: int = 60_000
    ai_generation_enabled: bool = True
    auto_generate_on_first_access: bool = True

    # --- mentor ------------------------------------------------------------
    mentor_model: str = "gemini-3.5-flash-lite"
    mentor_max_tokens: int = 600
    mentor_with_audio: bool = True

    # --- speech ------------------------------------------------------------
    tts_enabled: bool = True
    tts_model: str = "eleven-flash-v2.5"
    tts_cache_dir: str = "data/tts_cache"
    audio_url_prefix: str = "/audio"

    # --- realtime voice ----------------------------------------------------
    realtime_models: str = "gpt-realtime-2.1-mini,gpt-realtime-2.1,gemini-3.8-live"
    realtime_default_model: str = "gemini-3.8-live"
    realtime_url: str = ""

    # --- synchronisation --------------------------------------------------
    sync_min_interval_minutes: int = 1440

    # --- security ---------------------------------------------------------
    allowed_case_ids: str = ""
    cors_origins: str = "http://localhost:5173"

    # --- notifications -----------------------------------------------------
    notification_interval_seconds: int = 300

    # --- misc -------------------------------------------------------------
    plan_timezone: str = "America/Los_Angeles"
    log_level: str = "INFO"
    environment: str = "development"

    @field_validator("case_source")
    @classmethod
    def _validate_case_source(cls, value: str) -> str:
        allowed = {"auto", "mcp", "local"}
        normalized = (value or "auto").strip().lower()
        if normalized not in allowed:
            raise ValueError(f"case_source must be one of {sorted(allowed)}")
        return normalized

    @field_validator("ai_provider")
    @classmethod
    def _validate_ai_provider(cls, value: str) -> str:
        allowed = {"openai_compatible", "fake"}
        normalized = (value or "openai_compatible").strip().lower()
        if normalized not in allowed:
            raise ValueError(f"ai_provider must be one of {sorted(allowed)}")
        return normalized

    # --- derived helpers --------------------------------------------------

    @property
    def allowed_case_id_set(self) -> set[str]:
        """The allowlist of caseIds this instance may serve.

        Empty allowlist == deny everything (fail closed).  ``caseId`` is *not*
        an authentication mechanism; it is a guard rail for the prototype.
        """
        raw = self.allowed_case_ids or ""
        return {item.strip() for item in raw.split(",") if item.strip()}

    @property
    def cors_origin_list(self) -> list[str]:
        raw = self.cors_origins or ""
        return [item.strip() for item in raw.split(",") if item.strip()]

    @property
    def resolved_database_url(self) -> str:
        """Absolute SQLite path so the app does not depend on the CWD."""
        url = self.database_url
        prefix = "sqlite:///"
        if url.startswith(prefix):
            raw_path = url[len(prefix) :]
            if raw_path and raw_path != ":memory:":
                path = Path(raw_path)
                if not path.is_absolute():
                    path = (BASE_DIR / path).resolve()
                return f"{prefix}{path}"
        return url

    @property
    def resolved_cases_dir(self) -> Path:
        path = Path(self.cases_dir).expanduser()
        if not path.is_absolute():
            path = (BASE_DIR / path).resolve()
        return path

    @property
    def has_mcp_credentials(self) -> bool:
        return bool(self.mcp_url and self.mcp_token)

    @property
    def realtime_model_list(self) -> list[str]:
        """The voice models the proxy offers."""
        return [
            model.strip()
            for model in (self.realtime_models or "").split(",")
            if model.strip()
        ]

    @property
    def realtime_base_url(self) -> str:
        """The address of the realtime sessions.

        It comes from the AI proxy unless it is set on its own.
        """
        return self.realtime_url or self.ai_base_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
