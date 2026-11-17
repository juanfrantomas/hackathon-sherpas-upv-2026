"""The couple mode.

Two people share a plan and rarely want the same thing.  The mode shows the
portrait of each of them, the bridge towards a joint decision, the goals told
to the children and the wall of high fives.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from app.domain.couple import build_consensus_bridge, member_focus
from app.integration.ai.ai_service import AIService
from app.integration.mcp.context import CaseContext
from app.logging_config import get_logger
from app.repositories import family_high_five_repository
from app.schemas.couple import (
    CoupleMember,
    CoupleOverview,
    HighFiveItem,
    KidsGoalItem,
)

logger = get_logger(__name__)

COUPLE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["kids_safe_view"],
    "properties": {
        "kids_safe_view": {
            "type": "array",
            "maxItems": 4,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "id",
                    "icon",
                    "friendly_title",
                    "visual_meta",
                    "progress_percentage",
                    "children_explanation",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "icon": {"type": "string", "maxLength": 8},
                    "friendly_title": {"type": "string", "maxLength": 120},
                    "visual_meta": {"type": "string", "maxLength": 120},
                    "progress_percentage": {"type": "integer", "minimum": 0, "maximum": 100},
                    "children_explanation": {"type": "string", "maxLength": 300},
                },
            },
        }
    },
}

SYSTEM_PROMPT = """\
Eres elAside de Sherpas Wealth para las familias con hijos. Explicas a los
niños las metas de su familia sin mencionar cifras de adultos.

- Usa SOLO los datos del plan que te dan. No inventes importes ni plazos.
- Habla en un lenguaje de casa, sin palabras de banco.
- Cada objetivo va con su progreso real si el plan lo tiene.
- Escribe en el idioma del plan ({language}).
"""


class CoupleCopy(BaseModel):
    """The words of the couple mode."""

    model_config = ConfigDict(extra="forbid")

    kids_safe_view: list[dict[str, Any]] = Field(default_factory=list)


class CoupleService:
    """The portrait of a couple and the wall of their high fives."""

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

    async def overview(self, session: Session, case_id: str) -> CoupleOverview:
        """The state of the couple mode."""
        dynamics = await self._context.get_couple_dynamics(case_id)
        household = await self._context.get_compact_client_context(case_id)

        members = [
            CoupleMember(
                key=str(member.get("key") or ""),
                name=str(member.get("name") or ""),
                role=str(member.get("role") or ""),
                age=int(member.get("age") or 0),
                retirement_age=member.get("retirement_age"),
                risk_profile=str(member.get("risk_profile") or ""),
                personal_focus=str(member.get("personal_focus") or member_focus(None)),
            )
            for member in dynamics.get("members") or []
        ]

        copy = await self._write_copy(case_id, household)
        kids = [KidsGoalItem(**item) for item in copy.kids_safe_view]

        high_fives = [
            HighFiveItem.model_validate(high_five)
            for high_five in family_high_five_repository.list_high_fives(session, case_id)
        ]

        return CoupleOverview(
            case_id=case_id,
            is_couple=bool(dynamics.get("is_couple")),
            members=members,
            consensus_bridge=str(dynamics.get("consensus_bridge") or ""),
            kids_safe_view=kids,
            high_fives=high_fives,
            generated=bool(kids),
        )

    async def _write_copy(
        self, case_id: str, household: dict[str, Any]
    ) -> CoupleCopy:
        """The goals told to the children."""
        goals = await self._context.get_section(case_id, "financial-health", "goals")
        brief = {
            "household": household.get("household"),
            "children": household.get("children"),
            "goals": goals,
        }
        user = (
            "Estos son los datos del plan. Explica a los hijos las metas de su "
            "familia.\n\n" + json.dumps(brief, ensure_ascii=False, indent=2)
        )
        try:
            content = await self._ai.complete_json(
                system=SYSTEM_PROMPT.format(language="inglés"),
                user=user,
                schema=COUPLE_SCHEMA,
                model=self._model,
                max_tokens=self._max_tokens,
            )
            return CoupleCopy.model_validate(json.loads(content))
        except (ValidationError, json.JSONDecodeError) as exc:
            logger.warning("The goals for the children could not be read: %s", exc)
            return CoupleCopy()
        except Exception as exc:  # noqa: BLE001
            logger.warning("The goals for the children could not be written: %s", exc)
            return CoupleCopy()


def build_bridge(case_id: str, members: list[dict[str, Any]]) -> str:
    """The bridge towards a joint decision."""
    return build_consensus_bridge(case_id, members)
