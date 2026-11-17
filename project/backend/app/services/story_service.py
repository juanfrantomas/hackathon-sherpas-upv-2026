"""The financial story.

The four scenes that open the application of a household: where they are, the
tension that holds them back, what protects the children and the first step.
The figures come from the plan and the words from the model.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.voice_profiles import resolve_voice_profile
from app.integration.ai.ai_service import AIService
from app.integration.mcp.context import CaseContext
from app.logging_config import get_logger
from app.schemas.couple import StoryResponse, StoryScene

logger = get_logger(__name__)

STORY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["main_challenge", "scenes"],
    "properties": {
        "main_challenge": {"type": "string", "maxLength": 400},
        "scenes": {
            "type": "array",
            "minItems": 4,
            "maxItems": 4,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "scene_id",
                    "chapter",
                    "headline_figure",
                    "title",
                    "subtitle",
                    "caption_narration",
                ],
                "properties": {
                    "scene_id": {"type": "integer", "minimum": 1, "maximum": 4},
                    "chapter": {"type": "string", "maxLength": 80},
                    "headline_figure": {"type": "string", "maxLength": 40},
                    "title": {"type": "string", "maxLength": 160},
                    "subtitle": {"type": "string", "maxLength": 200},
                    "caption_narration": {"type": "string", "maxLength": 400},
                },
            },
        },
    },
}

SYSTEM_PROMPT = """\
Eres el narrador de Sherpas Wealth. Escribes las cuatro escenas de la
historia financiera de una familia.

- Usa SOLO las cifras del plan que te dan. No inventes importes ni fechas.
- La primera escena dice de dónde parten; la segunda, qué los frena; la
  tercera, a quién protegen; la cuarta, cuál es el primer paso.
- La narración se lee en voz alta: frases cortas, sin listas de números.
- Escribe en el idioma del plan ({language}) y en el registro indicado abajo.

{register}
"""


class StoryCopy(BaseModel):
    """The words of the story."""

    model_config = ConfigDict(extra="forbid")

    main_challenge: str = ""
    scenes: list[dict[str, Any]] = Field(default_factory=list)


class StoryService:
    """The introductory story of a household."""

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

    async def story(self, case_id: str) -> StoryResponse:
        """The package of the story."""
        household = await self._context.get_compact_client_context(case_id)
        profile = resolve_voice_profile(household.get("classification"))

        score = await self._context.get_section(case_id, "financial-health", "score")
        score = score if isinstance(score, dict) else {}
        narrative = await self._context.get_section(
            case_id, "financial-health", "narrative"
        )
        narrative = narrative if isinstance(narrative, dict) else {}

        copy = await self._write_copy(case_id, household, score, narrative)

        scenes = [StoryScene(**scene) for scene in copy.scenes]
        names = [
            str(adult.get("first_name") or "")
            for adult in (household.get("adults") or [])
        ]
        case_block = household.get("household") or {}

        first_step: dict[str, Any] = {}
        top_moves = score.get("top_moves") or []
        if top_moves:
            move = top_moves[0]
            first_step = {
                "title": move.get("title"),
                "action": move.get("action"),
                "score_before": move.get("score_before"),
                "score_after": move.get("score_after"),
            }

        return StoryResponse(
            case_id=case_id,
            short_id=_short_id(case_id),
            household_title=" & ".join(name for name in names if name) or case_id,
            city=str(case_block.get("city") or ""),
            state=str(case_block.get("state") or ""),
            is_couple=bool(household.get("is_couple")),
            score=int(score.get("published_score") or 0),
            band=str(score.get("band") or ""),
            voice_name=profile["voice_name"],
            style_key=profile["style_key"],
            style_label=profile["style_label"],
            main_challenge=copy.main_challenge,
            scenes=scenes,
            full_narration_script=" ".join(
                scene.caption_narration for scene in scenes
            ),
            first_step_cta=first_step,
            generated=bool(scenes),
        )

    async def _write_copy(
        self,
        case_id: str,
        household: dict[str, Any],
        score: dict[str, Any],
        narrative: dict[str, Any],
    ) -> StoryCopy:
        """The words of the story, written by the model."""
        profile = resolve_voice_profile(household.get("classification"))
        brief = {
            "household": household.get("household"),
            "adults": household.get("adults"),
            "children": household.get("children"),
            "score": score,
            "narrative": narrative,
        }
        user = (
            "Estos son los datos del plan. Escribe las cuatro escenas de la "
            "historia.\n\n" + json.dumps(brief, ensure_ascii=False, indent=2)
        )
        try:
            content = await self._ai.complete_json(
                system=SYSTEM_PROMPT.format(
                    language="inglés", register=profile.get("tone_instructions", "")
                ),
                user=user,
                schema=STORY_SCHEMA,
                model=self._model,
                max_tokens=self._max_tokens,
            )
            return StoryCopy.model_validate(json.loads(content))
        except (ValidationError, json.JSONDecodeError) as exc:
            logger.warning("The story could not be read: %s", exc)
            return StoryCopy()
        except Exception as exc:  # noqa: BLE001
            logger.warning("The story could not be written: %s", exc)
            return StoryCopy()


def _short_id(case_id: str) -> str:
    from app.domain.cases import get_short_id

    return get_short_id(case_id)
