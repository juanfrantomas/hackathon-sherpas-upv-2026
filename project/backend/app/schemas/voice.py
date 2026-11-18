"""API schemas for the mentor and the voice."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MentorAskRequest(BaseModel):
    """A question from the household."""

    case_id: str = Field(description="The household the question is about")
    question: str = Field(min_length=1, max_length=2000)
    style: str | None = Field(
        default=None, description="The register the household asks for"
    )
    partner: str | None = Field(
        default=None, description="Which member of the couple is speaking"
    )
    topic: str | None = Field(
        default=None, description="The milestone the household opened"
    )


class MentorAskResponse(BaseModel):
    """The answer of the mentor."""

    status: str = "success"
    case_id: str
    short_id: str
    mcp_used: bool = False
    voice: str
    style: str
    style_key: str
    partner_mode: str | None = None
    consulted: list[str] = Field(default_factory=list)
    answer: str
    audio_url: str | None = None


class VoiceProfileResponse(BaseModel):
    """The register of a household."""

    style_key: str
    style_label: str
    voice_name: str
    gemini_voice: str
    openai_voice: str
