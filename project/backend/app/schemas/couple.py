"""API schemas for the couple mode and the financial story."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CoupleMember(BaseModel):
    """One member of the household."""

    key: str
    name: str
    role: str
    age: int
    retirement_age: int | None = None
    risk_profile: str
    personal_focus: str


class KidsGoalItem(BaseModel):
    """A goal of the household, told to the children."""

    id: str
    icon: str = ""
    friendly_title: str = ""
    visual_meta: str = ""
    progress_percentage: int = 0
    children_explanation: str = ""


class HighFiveItem(BaseModel):
    """A high five between the two members of a couple."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    from_member: str
    to_member: str
    milestone_title: str
    message: str
    created_at: datetime


class CoupleOverview(BaseModel):
    """The state of the couple mode."""

    case_id: str
    is_couple: bool
    members: list[CoupleMember] = Field(default_factory=list)
    consensus_bridge: str = ""
    kids_safe_view: list[KidsGoalItem] = Field(default_factory=list)
    high_fives: list[HighFiveItem] = Field(default_factory=list)
    generated: bool = False


class HighFiveRequest(BaseModel):
    """A high five the household sends to each other."""

    from_member: str
    to_member: str
    milestone_title: str
    message: str = "¡Choca esos cinco! Un paso más cerca de nuestra meta familiar 👋"


class StoryScene(BaseModel):
    """One scene of the financial story."""

    scene_id: int
    chapter: str
    headline_figure: str
    title: str
    subtitle: str
    caption_narration: str


class StoryResponse(BaseModel):
    """The package of the introductory story."""

    case_id: str
    short_id: str
    household_title: str
    city: str = ""
    state: str = ""
    is_couple: bool = False
    score: int = 0
    band: str = ""
    voice_name: str = ""
    style_key: str = ""
    style_label: str = ""
    main_challenge: str = ""
    scenes: list[StoryScene] = Field(default_factory=list)
    full_narration_script: str = ""
    first_step_cta: dict = Field(default_factory=dict)
    generated: bool = False
