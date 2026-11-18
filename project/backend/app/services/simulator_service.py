"""The decision laboratory.

The score comes from the plan; the words come from the model.  When the model
is not available the service still answers with the figures of the plan, so
the laboratory is never empty.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.simulator import PowerUp, Simulation, simulate
from app.integration.ai.ai_service import AIService
from app.integration.mcp.context import CaseContext
from app.logging_config import get_logger
from app.schemas.simulator import (
    DecisionPowerUp,
    PactCard,
    SimulatorResponse,
    TimelineComparison,
)

logger = get_logger(__name__)

SIMULATOR_COPY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "synergy_message",
        "combo_mentor_question",
        "annual_saving_dollars",
        "saving_label",
        "time_impact",
        "visual_summary",
        "power_up_copy",
        "timeline_comparison",
        "pact_cards",
    ],
    "properties": {
        "synergy_message": {"type": "string", "maxLength": 400},
        "combo_mentor_question": {"type": "string", "maxLength": 300},
        "annual_saving_dollars": {"type": "integer", "minimum": 0},
        "saving_label": {"type": "string", "maxLength": 120},
        "time_impact": {"type": "string", "maxLength": 200},
        "visual_summary": {"type": "string", "maxLength": 400},
        "power_up_copy": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "icon", "effort", "lock_label", "individual_impact", "mentor_question"],
                "properties": {
                    "id": {"type": "string"},
                    "icon": {"type": "string", "maxLength": 8},
                    "effort": {"type": "string", "maxLength": 80},
                    "lock_label": {"type": "string", "maxLength": 80},
                    "individual_impact": {"type": "string", "maxLength": 300},
                    "mentor_question": {"type": "string", "maxLength": 300},
                },
            },
        },
        "timeline_comparison": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["milestone", "icon", "without_changes", "with_decisions", "highlighted_change"],
                "properties": {
                    "milestone": {"type": "string", "maxLength": 120},
                    "icon": {"type": "string", "maxLength": 8},
                    "without_changes": {"type": "string", "maxLength": 300},
                    "with_decisions": {"type": "string", "maxLength": 300},
                    "highlighted_change": {"type": "string", "maxLength": 160},
                },
            },
        },
        "pact_cards": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "card_id",
                    "icon",
                    "title",
                    "subtitle_for",
                    "peace_percentage",
                    "return_percentage",
                    "resulting_score",
                    "verdict",
                    "mentor_question",
                    "recommended",
                ],
                "properties": {
                    "card_id": {"type": "string"},
                    "icon": {"type": "string", "maxLength": 8},
                    "title": {"type": "string", "maxLength": 160},
                    "subtitle_for": {"type": "string", "maxLength": 160},
                    "peace_percentage": {"type": "integer", "minimum": 0, "maximum": 100},
                    "return_percentage": {"type": "integer", "minimum": 0, "maximum": 100},
                    "resulting_score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "verdict": {"type": "string", "maxLength": 300},
                    "mentor_question": {"type": "string", "maxLength": 300},
                    "recommended": {"type": "boolean"},
                },
            },
        },
    },
}


class SimulatorCopy(BaseModel):
    """The words of the laboratory."""

    model_config = ConfigDict(extra="forbid")

    synergy_message: str = ""
    combo_mentor_question: str = ""
    annual_saving_dollars: int = 0
    saving_label: str = ""
    time_impact: str = ""
    visual_summary: str = ""
    power_up_copy: list[dict[str, Any]] = Field(default_factory=list)
    timeline_comparison: list[dict[str, Any]] = Field(default_factory=list)
    pact_cards: list[dict[str, Any]] = Field(default_factory=list)


SYSTEM_PROMPT = """\
Eres el motor del laboratorio de decisiones de Sherpas Wealth. Explicas a una
familia qué cambia en su plan si activan una decisión.

- Usa SOLO las cifras del plan que te dan. No inventes importes, plazos ni
  puntuaciones.
- La puntuación y los saltos de puntos ya te los dan calculados: no los
  recalcules ni los contradigas.
- Escribe en el idioma del plan ({language}), en el registro indicated below.
- Usa comparaciones con la vida de casa, no lenguaje de banco.
- La sinopsis visual es la frase que la familia ve en grande: una sola idea.

{register}
"""


class SimulatorService:
    """Shows what the plan says about the decisions of a household."""

    def __init__(
        self,
        ai_service: AIService,
        context: CaseContext,
        *,
        model: str | None = None,
        max_tokens: int = 8000,
    ) -> None:
        self._ai = ai_service
        self._context = context
        self._model = model
        self._max_tokens = max_tokens

    async def simulate(
        self, case_id: str, active_ids: list[str] | None = None
    ) -> SimulatorResponse:
        """The laboratory for a household."""
        household = await self._context.get_compact_client_context(case_id)
        score_block = await self._context.get_section(
            case_id, "financial-health", "score"
        )
        if not isinstance(score_block, dict):
            score_block = {}

        simulation = simulate(score_block, active_ids)
        names = [
            str(adult.get("first_name") or "")
            for adult in (household.get("adults") or [])
        ]

        copy = await self._write_copy(case_id, score_block, simulation, household)

        power_ups = [
            _to_power_up(power_up, copy) for power_up in simulation.power_ups
        ]
        timeline = [
            TimelineComparison(**item) for item in copy.timeline_comparison
        ]
        pacts = [PactCard(**item) for item in copy.pact_cards]

        return SimulatorResponse(
            case_id=case_id,
            short_id=_short_id(case_id),
            household_name=" & ".join(name for name in names if name) or case_id,
            score_base=simulation.score_base,
            simulated_score=simulation.score_simulated,
            score_delta=simulation.score_delta,
            synergy_detected=simulation.synergy_detected,
            synergy_message=copy.synergy_message,
            combo_mentor_question=copy.combo_mentor_question,
            annual_saving_dollars=copy.annual_saving_dollars,
            saving_label=copy.saving_label,
            time_impact=copy.time_impact,
            visual_summary=copy.visual_summary or copy.synergy_message,
            confetti=simulation.synergy_detected and simulation.score_delta > 0,
            power_ups=power_ups,
            timeline_comparison=timeline,
            pact_cards=pacts,
            generated=bool(copy.timeline_comparison or copy.pact_cards),
        )

    async def _write_copy(
        self,
        case_id: str,
        score_block: dict[str, Any],
        simulation: Simulation,
        household: dict[str, Any],
    ) -> SimulatorCopy:
        """The words of the laboratory, written by the model."""
        from app.domain.voice_profiles import resolve_voice_profile

        profile = resolve_voice_profile(household.get("classification"))
        brief = {
            "household": household.get("household"),
            "score": score_block,
            "steps": [
                {
                    "title": power_up.title,
                    "action": power_up.action,
                    "score_before": power_up.score_before,
                    "score_after": power_up.score_after,
                    "active": power_up.active,
                }
                for power_up in simulation.power_ups
            ],
            "active_ids": simulation.active_ids,
            "score_base": simulation.score_base,
            "simulated_score": simulation.score_simulated,
            "score_delta": simulation.score_delta,
            "synergy_detected": simulation.synergy_detected,
            "synergy_score": simulation.synergy_score,
        }
        user = (
            "Estas son las decisiones y sus cifras. Escribe los textos del "
            "laboratorio.\n\n"
            + json.dumps(brief, ensure_ascii=False, indent=2)
        )
        try:
            content = await self._ai.complete_json(
                system=SYSTEM_PROMPT.format(
                    language="español de España"
                    if "español" in str(profile.get("tone_instructions", "")).lower()
                    or profile.get("style_key") == "formal"
                    else "inglés",
                    register=profile.get("tone_instructions", ""),
                ),
                user=user,
                schema=SIMULATOR_COPY_SCHEMA,
                model=self._model,
                max_tokens=self._max_tokens,
            )
            return SimulatorCopy.model_validate(json.loads(content))
        except (ValidationError, json.JSONDecodeError) as exc:
            logger.warning("The laboratory copy could not be read: %s", exc)
            return SimulatorCopy()
        except Exception as exc:  # noqa: BLE001 - the figures still reach the client
            logger.warning("The laboratory copy could not be written: %s", exc)
            return SimulatorCopy()


def _to_power_up(power_up: PowerUp, copy: SimulatorCopy) -> DecisionPowerUp:
    """A decision of the plan, with the words the model wrote for it."""
    written = next(
        (item for item in copy.power_up_copy if item.get("id") == power_up.id), {}
    )
    return DecisionPowerUp(
        id=power_up.id,
        icon=str(written.get("icon") or "⭐"),
        title=power_up.title,
        short_action=power_up.action,
        effort=str(written.get("effort") or ""),
        lock_label=str(written.get("lock_label") or ""),
        individual_impact=str(written.get("individual_impact") or ""),
        mentor_question=str(written.get("mentor_question") or ""),
        score_before=power_up.score_before,
        score_after=power_up.score_after,
        score_impact=power_up.score_impact,
        active=power_up.active,
    )


def _short_id(case_id: str) -> str:
    from app.domain.cases import get_short_id

    return get_short_id(case_id)
