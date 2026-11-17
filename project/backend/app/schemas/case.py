"""The catalogue of the households the backend can serve."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CaseSummary(BaseModel):
    """One household, with the register the mentor will use with it."""

    model_config = ConfigDict(from_attributes=True)

    case_id: str
    short_id: str
    household_name: str
    city: str | None = None
    state: str | None = None
    is_couple: bool
    members: list[str]
    score: int | None = None
    band: str | None = None
    voice_style: str
    voice_label: str
    voice_name: str
    gemini_voice: str
    openai_voice: str
