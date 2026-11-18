"""The proactive mentor and the translator of jargon.

Both are written by the model, from the plan: the nudge comes from the
concern the plan reports and the pills translate the terms the plan uses into
comparisons of everyday life.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.voice_profiles import resolve_voice_profile
from app.integration.ai.ai_service import AIService
from app.integration.mcp.context import CaseContext
from app.logging_config import get_logger
from app.schemas.simulator import (
    JargonPill,
    MentorInsightsResponse,
    ProactiveInsight,
)

logger = get_logger(__name__)

INSIGHTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["proactive_nudge", "jargon_pills"],
    "properties": {
        "proactive_nudge": {
            "type": "object",
            "additionalProperties": False,
            "required": ["badge", "greeting", "message", "cta_label", "voice_question"],
            "properties": {
                "badge": {"type": "string", "maxLength": 40},
                "greeting": {"type": "string", "maxLength": 120},
                "message": {"type": "string", "maxLength": 400},
                "cta_label": {"type": "string", "maxLength": 60},
                "voice_question": {"type": "string", "maxLength": 300},
            },
        },
        "jargon_pills": {
            "type": "array",
            "maxItems": 4,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "term",
                    "short_tag",
                    "metaphor_title",
                    "metaphor_explanation",
                    "family_impact",
                    "voice_question",
                ],
                "properties": {
                    "term": {"type": "string", "maxLength": 80},
                    "short_tag": {"type": "string", "maxLength": 60},
                    "metaphor_title": {"type": "string", "maxLength": 120},
                    "metaphor_explanation": {"type": "string", "maxLength": 400},
                    "family_impact": {"type": "string", "maxLength": 300},
                    "voice_question": {"type": "string", "maxLength": 300},
                },
            },
        },
    },
}

SYSTEM_PROMPT = """\
Eres el mentor proactivo de Sherpas Wealth. Dejas una sola aviso útil en la
puerta de la familia y traduce el lenguaje del banco a palabras de casa.

- Usa SOLO los datos del plan que te dan. No inventes cifras.
- El aviso proactivo tiene que señalar un paso concreto y accionable, no un
  resumen del plan.
- Las píldoras de jerga traducen términos financieros que aparecen EN el
  plan de esta familia a comparaciones cotidianas.
- Escribe en el idioma del plan ({language}) y en el registro indicado abajo.

{register}
"""


class InsightsCopy(BaseModel):
    """The words of the proactive mentor."""

    model_config = ConfigDict(extra="forbid")

    proactive_nudge: dict[str, Any] = Field(default_factory=dict)
    jargon_pills: list[dict[str, Any]] = Field(default_factory=list)


class InsightsService:
    """The proactive mentor of the households."""

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

    async def insights(self, case_id: str) -> MentorInsightsResponse:
        """The nudge and the jargon pills of a household."""
        household = await self._context.get_compact_client_context(case_id)
        profile = resolve_voice_profile(household.get("classification"))

        concerns = await self._context.get_section(
            case_id, "persona", "Objective concerns"
        )
        tensions = await self._context.get_section(case_id, "persona", "Tensions")
        score = await self._context.get_section(case_id, "financial-health", "score")

        copy = await self._write_copy(case_id, household, concerns, tensions, score)

        nudge = ProactiveInsight(**copy.proactive_nudge) if copy.proactive_nudge else ProactiveInsight()
        pills = [JargonPill(**pill) for pill in copy.jargon_pills]

        return MentorInsightsResponse(
            case_id=case_id,
            short_id=_short_id(case_id),
            style_key=profile["style_key"],
            style_label=profile["style_label"],
            proactive_nudge=nudge,
            jargon_pills=pills,
            generated=bool(pills or copy.proactive_nudge),
        )

    async def _write_copy(
        self,
        case_id: str,
        household: dict[str, Any],
        concerns: Any,
        tensions: Any,
        score: Any,
    ) -> InsightsCopy:
        """The words of the mentor, written by the model."""
        profile = resolve_voice_profile(household.get("classification"))
        brief = {
            "household": household.get("household"),
            "adults": household.get("adults"),
            "score": score,
            "objective_concerns": concerns,
            "tensions": tensions,
        }
        user = (
            "Estos son los datos del plan de la familia. Escribe el aviso "
            "proactivo y las píldoras de jerga.\n\n"
            + json.dumps(brief, ensure_ascii=False, indent=2)
        )
        try:
            content = await self._ai.complete_json(
                system=SYSTEM_PROMPT.format(
                    language="inglés", register=profile.get("tone_instructions", "")
                ),
                user=user,
                schema=INSIGHTS_SCHEMA,
                model=self._model,
                max_tokens=self._max_tokens,
            )
            return InsightsCopy.model_validate(json.loads(content))
        except (ValidationError, json.JSONDecodeError) as exc:
            logger.warning("The insights could not be read: %s", exc)
            return InsightsCopy()
        except Exception as exc:  # noqa: BLE001
            logger.warning("The insights could not be written: %s", exc)
            return InsightsCopy()


def _short_id(case_id: str) -> str:
    from app.domain.cases import get_short_id

    return get_short_id(case_id)
