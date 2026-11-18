"""The mentor.

It answers a question about the plan of a household.  It may ask the plan for
a detail it does not have in its brief, it speaks in the register the
household needs and it can answer with a voice.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app.domain.voice_profiles import resolve_voice_profile
from app.integration.ai.ai_service import AIService
from app.integration.mcp.context import CaseContext, as_json
from app.logging_config import get_logger
from app.services.tts_service import TtsService

logger = get_logger(__name__)

#: The tool the mentor may call to read the plan.
GET_CASE_PARAM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "part": {
            "type": "string",
            "enum": ["financial-health", "investment-analysis", "persona"],
        },
        "section": {
            "type": "string",
            "enum": [
                "score",
                "goals",
                "profile",
                "narrative",
                "projections",
                "key_metrics",
                "positions",
                "analysis",
                "D0",
                "D1",
                "D2",
                "D3",
                "D4",
                "D5",
                "D6",
                "Transition alerts",
                "Objective concerns",
                "Tensions",
            ],
            "description": (
                "Sección: 'positions' (ETFs/cartera), 'projections' (hitos anuales), "
                "'profile' (cuentas/deudas/seguros), 'goals', 'key_metrics', 'Tensions'."
            ),
        },
        "sub_section": {
            "type": "string",
            "description": (
                "Sub-clave opcional de profile ('incomes','expenses','accounts',"
                "'liabilities','insurance') o key_metrics ('debtManagement','protection',"
                "'cashflowStatement','retirementAndOtherGoals','portfolioAnalysis',"
                "'taxDragAnalysis')."
            ),
        },
    },
    "required": ["part", "section"],
}

#: The tool the mentor offers to the model.
MENTOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_case",
            "description": "Consulta una sección o sub-sección del expediente financiero del cliente.",
            "parameters": GET_CASE_PARAM_SCHEMA,
        },
    }
]

SYSTEM_PROMPT = (
    "Eres el asesor de Sherpas Wealth, pero NO hablas como un banco aburrido.\n"
    "{tone_instructions}\n\n"
    "REGLA DE ORO: PROHIBIDO recitar listas largas de cifras o decimales. "
    "Usa los datos reales del plan como tu chuleta interna y tradúcelos al registro "
    "del cliente en máximo 2 o 3 frases vivas y directas.\n\n"
    "CHULETA INTERNA:\n{brief}"
)


@dataclass
class MentorAnswer:
    """What the mentor answered."""

    text: str = ""
    mcp_used: bool = False
    consulted: list[str] = field(default_factory=list)
    voice_profile: dict[str, str] = field(default_factory=dict)
    audio_url: str | None = None
    audio_cached: bool = False


class MentorService:
    """Answers the questions of a household about their plan."""

    def __init__(
        self,
        ai_service: AIService,
        context: CaseContext,
        tts_service: TtsService | None = None,
        *,
        model: str | None = None,
        max_tokens: int = 600,
        with_audio: bool = True,
    ) -> None:
        self._ai = ai_service
        self._context = context
        self._tts = tts_service
        self._model = model
        self._max_tokens = max_tokens
        self._with_audio = with_audio

    async def ask(
        self,
        *,
        case_id: str,
        question: str,
        style: str | None = None,
        partner: str | None = None,
        topic: str | None = None,
    ) -> MentorAnswer:
        """Answer a question about the plan of a household."""
        household = await self._context.get_compact_client_context(case_id)
        brief = await self._context.build_realtime_brief(
            case_id, partner=partner, topic=topic
        )
        voice_profile = resolve_voice_profile(
            household.get("classification"),
            style_override=None if style in (None, "auto") else style,
        )

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(
                    tone_instructions=voice_profile["tone_instructions"],
                    brief=brief,
                ),
            },
            {"role": "user", "content": question},
        ]

        consulted: list[str] = []

        async def handle_tool(name: str, arguments: dict[str, Any]) -> str:
            part = str(arguments.get("part") or "financial-health")
            section = arguments.get("section")
            sub_section = arguments.get("sub_section")
            label = f"{part}.{section}" + (f".{sub_section}" if sub_section else "")
            try:
                data = await self._context.get_section(
                    case_id,
                    part,
                    str(section) if section else None,
                    str(sub_section) if sub_section else None,
                    compact_for_llm=True,
                )
            except Exception as exc:  # noqa: BLE001 - the model must not crash
                logger.warning("The mentor could not read %s: %s", label, exc)
                return json.dumps({"error": str(exc)}, ensure_ascii=False)
            consulted.append(label)
            return as_json(data)

        outcome = await self._ai.chat_with_tools(
            messages=messages,
            tools=MENTOR_TOOLS,
            tool_handler=handle_tool,
            model=self._model,
            max_tokens=self._max_tokens,
        )

        answer = MentorAnswer(
            text=outcome.content,
            mcp_used=bool(consulted),
            consulted=consulted,
            voice_profile=voice_profile,
        )

        if self._with_audio and self._tts is not None and answer.text:
            audio = await self._tts.synthesize(answer.text, voice_profile)
            if audio.filename:
                answer.audio_url = audio.url_path
                answer.audio_cached = audio.cached
        return answer
