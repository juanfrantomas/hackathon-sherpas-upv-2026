"""API schemas for the decision laboratory, the insights and the story."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DecisionPowerUp(BaseModel):
    """One decision the household can switch on."""

    id: str
    icon: str = ""
    title: str
    short_action: str = ""
    effort: str = ""
    lifts_a_cap: bool = False
    lock_label: str = ""
    individual_impact: str = ""
    mentor_question: str = ""
    score_before: int = 0
    score_after: int = 0
    score_impact: int = 0
    active: bool = False


class TimelineComparison(BaseModel):
    """One moment of the family, with and without the decisions."""

    milestone: str
    icon: str = ""
    without_changes: str
    with_decisions: str
    highlighted_change: str


class PactCard(BaseModel):
    """The agreement between the two members of a couple."""

    card_id: str
    icon: str = ""
    title: str
    subtitle_for: str = ""
    peace_percentage: int = 0
    return_percentage: int = 0
    resulting_score: int = 0
    verdict: str = ""
    mentor_question: str = ""
    recommended: bool = False


class SimulatorRequest(BaseModel):
    """The decisions the household switched on."""

    active_ids: list[str] = Field(default_factory=list)


class SimulatorResponse(BaseModel):
    """What the plan says about those decisions."""

    case_id: str
    short_id: str
    household_name: str = ""
    score_base: int = 0
    simulated_score: int = 0
    score_delta: int = 0
    synergy_detected: bool = False
    synergy_message: str = ""
    combo_mentor_question: str = ""
    annual_saving_dollars: int = 0
    saving_label: str = ""
    time_impact: str = ""
    visual_summary: str = ""
    confetti: bool = False
    power_ups: list[DecisionPowerUp] = Field(default_factory=list)
    timeline_comparison: list[TimelineComparison] = Field(default_factory=list)
    pact_cards: list[PactCard] = Field(default_factory=list)
    generated: bool = Field(
        default=False, description="False when the copy could not be written"
    )


class JargonPill(BaseModel):
    """A financial term, explained with a comparison of everyday life."""

    term: str
    short_tag: str = ""
    metaphor_title: str = ""
    metaphor_explanation: str = ""
    family_impact: str = ""
    voice_question: str = ""


class ProactiveInsight(BaseModel):
    """The nudge the mentor leaves on the door."""

    badge: str = ""
    greeting: str = ""
    message: str = ""
    cta_label: str = ""
    voice_question: str = ""


class MentorInsightsResponse(BaseModel):
    """The proactive mentor and the translator of jargon."""

    case_id: str
    short_id: str
    style_key: str
    style_label: str
    proactive_nudge: ProactiveInsight
    jargon_pills: list[JargonPill] = Field(default_factory=list)
    generated: bool = False
