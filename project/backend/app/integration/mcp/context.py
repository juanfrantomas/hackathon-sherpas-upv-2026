"""Reading a case for a conversation.

The mentor needs the plan in small pieces: the household, the score, the gaps
the persona reports and the tensions between the two partners.  This module
reads them from a case source (the MCP or the offline files) and hands them
over ready for a prompt.
"""

from __future__ import annotations

import json
import time
from typing import Any

from app.integration.mcp.case_source import CaseSource
from app.integration.mcp.compaction import compact_payload
from app.integration.mcp.normalizer import extract_persona_section

#: How long a part stays in memory.
_CACHE_TTL_SECONDS = 3600.0


class CaseContext:
    """Reads the plan of a case in the shape a conversation needs."""

    def __init__(self, source: CaseSource) -> None:
        self._source = source
        self._parts: dict[str, tuple[float, Any]] = {}

    # -- parts -----------------------------------------------------------

    async def get_part(self, case_id: str, part: str) -> Any:
        """A whole part of the case, cached."""
        key = f"{case_id}::{part}"
        cached = self._parts.get(key)
        if cached is not None and cached[0] > time.monotonic():
            return cached[1]
        payload = await self._source.get_part(case_id, part)
        self._parts[key] = (time.monotonic() + _CACHE_TTL_SECONDS, payload)
        return payload

    async def get_section(
        self,
        case_id: str,
        part: str,
        section: str | None = None,
        sub_section: str | None = None,
        compact_for_llm: bool = False,
    ) -> Any:
        """One section of a part, optionally compacted for the model."""
        document = await self.get_part(case_id, part)

        raw: Any
        if part == "persona":
            raw = extract_persona_section(
                document if isinstance(document, str) else str(document or ""), section
            )
        elif section and isinstance(document, dict):
            if section in document:
                raw = document[section]
            else:
                raw = {
                    "_error": (
                        f"Sección '{section}' no encontrada. "
                        f"Disponibles: {list(document.keys())}"
                    )
                }
        else:
            raw = document

        if compact_for_llm or sub_section:
            return compact_payload(raw, section, sub_section)
        return raw

    # -- the household ----------------------------------------------------

    async def get_compact_client_context(self, case_id: str) -> dict[str, Any]:
        """The light context of the household.

        The members, whether it is a couple, the published score and the
        psychological classification.
        """
        case_info = await self.get_section(case_id, "financial-health", "case")
        score_info = await self.get_section(case_id, "financial-health", "score")
        classification = await self.get_section(case_id, "persona", "classification")

        household = (
            case_info.get("household") if isinstance(case_info, dict) else []
        ) or []
        adults = [member for member in household if member.get("role") in ("client", "co-client")]
        children = [member for member in household if member.get("role") == "child"]

        return {
            "case_id": case_id,
            "household": case_info,
            "adults": adults,
            "children": children,
            "is_couple": len(adults) >= 2,
            "score_summary": {
                "published_score": (
                    score_info.get("published_score") if isinstance(score_info, dict) else None
                ),
                "band": score_info.get("band") if isinstance(score_info, dict) else None,
            },
            "classification": classification,
        }

    async def get_couple_dynamics(self, case_id: str) -> dict[str, Any]:
        """The portrait of the couple.

        The risk profile of each partner, how they share the decisions, the
        tensions the plan reports between them and a bridge towards a joint
        decision.
        """
        from app.domain.couple import build_consensus_bridge, member_focus

        context = await self.get_compact_client_context(case_id)
        adults = context["adults"]

        risk = await self.get_section(case_id, "persona", "D4")
        style = await self.get_section(case_id, "persona", "D5")
        tensions = await self.get_section(case_id, "persona", "Tensions")

        members: list[dict[str, Any]] = []
        for adult in adults:
            name = adult.get("first_name", "")
            risk_profile = adult.get("risk_profile", "Moderate")
            members.append(
                {
                    "key": name.lower(),
                    "name": name,
                    "role": adult.get("role"),
                    "age": adult.get("age"),
                    "retirement_age": adult.get("retirement_age", 62),
                    "risk_profile": risk_profile,
                    "personal_focus": member_focus(risk_profile),
                }
            )

        return {
            "case_id": case_id,
            "is_couple": context["is_couple"],
            "members": members,
            "decision_style": style,
            "risk_alignment": risk,
            "tensions": tensions,
            "consensus_bridge": build_consensus_bridge(case_id, members),
        }

    # -- the brief for a conversation --------------------------------------

    async def build_realtime_brief(
        self,
        case_id: str,
        *,
        partner: str | None = None,
        topic: str | None = None,
    ) -> str:
        """The internal note the mentor keeps in front of it.

        It holds the household, the score, the steps that raise it, the gaps
        the persona reports, the couple mode and the topic the household
        opened.  It is written for the model, not for the client.
        """
        from app.domain.couple import build_partner_instruction

        case_info = await self.get_section(case_id, "financial-health", "case")
        score_info = await self.get_section(case_id, "financial-health", "score")
        narrative = await self.get_section(case_id, "financial-health", "narrative")
        gaps = await self.get_section(case_id, "persona", "D3")
        alerts = await self.get_section(case_id, "persona", "Transition alerts")
        couple = await self.get_couple_dynamics(case_id)

        household = (
            case_info.get("household") if isinstance(case_info, dict) else []
        ) or []
        people = ", ".join(
            f"{member.get('first_name')} ({member.get('role')}, {member.get('age')} años)"
            for member in household
        )
        city = case_info.get("city", "") if isinstance(case_info, dict) else ""
        state = case_info.get("state", "") if isinstance(case_info, dict) else ""

        score_value = (
            score_info.get("published_score") if isinstance(score_info, dict) else "N/A"
        )
        score_band = score_info.get("band", "") if isinstance(score_info, dict) else ""
        top_moves = (
            score_info.get("top_moves") if isinstance(score_info, dict) else []
        ) or []
        combined_moves = (
            score_info.get("combined_moves") if isinstance(score_info, dict) else []
        ) or []

        moves_text = "; ".join(
            f"{move.get('title')}: {move.get('action')} "
            f"(Score {move.get('score_before')}->{move.get('score_after')})"
            for move in top_moves
        )
        if combined_moves:
            best = max(combined_moves, key=lambda item: item.get("score_after", 0))
            moves_text += (
                f" | COMBINADOS ({' + '.join(best.get('moves', []))}): "
                f"sube el Score hasta {best.get('score_after')}."
            )

        recommendation = ""
        if isinstance(narrative, dict):
            recommendation = narrative.get("summary_recommendations") or ""

        # The alerts are dropped when there are none: they cost tokens on
        # every single turn.
        clean_alerts = ""
        if isinstance(alerts, str) and "none detected" not in alerts.lower():
            clean_alerts = alerts

        partner_block = build_partner_instruction(couple, partner)
        topic_block = (
            f"TEMA ACTIVO SELECCIONADO POR EL CLIENTE EN LA APP: '{topic}'. "
            "Céntrate directamente en resolver y guiar sobre este punto."
            if topic
            else ""
        )

        parts = [
            f"HOGAR: {people} ({city}, {state}). SCORE: {score_value}/100 ({score_band}).",
            partner_block,
            topic_block,
            moves_text and f"PASOS QUE SUBEN SU SCORE:\n{moves_text}",
            f"RESUMEN DE SITUACIÓN Y BRECHAS (D3):\n{gaps}",
            clean_alerts and f"ALERTA INMINENTE:\n{clean_alerts}",
            recommendation and f"RECOMENDACIÓN CLAVE DE SHERPAS:\n{recommendation}",
        ]
        return "\n\n".join(part for part in parts if part)


def as_json(payload: Any) -> str:
    """The payload as the compact JSON the model reads."""
    if isinstance(payload, str):
        return payload
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
