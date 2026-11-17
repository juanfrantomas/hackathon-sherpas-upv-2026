"""The directory of the households.

It answers "who can the mentor talk to, and in which register", which is the
first thing the client asks for when it opens the mentor.
"""

from __future__ import annotations

from typing import Any

from app.domain.cases import get_short_id
from app.domain.voice_profiles import resolve_voice_profile
from app.integration.mcp.case_source import CaseSource
from app.integration.mcp.context import CaseContext
from app.logging_config import get_logger
from app.schemas.case import CaseSummary

logger = get_logger(__name__)


async def list_cases(source: CaseSource, context: CaseContext) -> list[CaseSummary]:
    """Every household the source knows, with its voice profile."""
    known = await source.list_cases()
    summaries: list[CaseSummary] = []

    for entry in known:
        case_id = str(entry.get("caseId") or entry.get("case_id") or "")
        if not case_id:
            continue
        try:
            household = await context.get_compact_client_context(case_id)
        except Exception as exc:  # noqa: BLE001 - one broken case must not break the list
            logger.warning("Could not read the household %s: %s", case_id, exc)
            continue

        adults: list[dict[str, Any]] = household.get("adults") or []
        profile = resolve_voice_profile(household.get("classification"))
        names = [str(adult.get("first_name") or "") for adult in adults]

        summaries.append(
            CaseSummary(
                case_id=case_id,
                short_id=get_short_id(case_id),
                household_name=" & ".join(name for name in names if name) or case_id,
                city=(household.get("household") or {}).get("city"),
                state=(household.get("household") or {}).get("state"),
                is_couple=bool(household.get("is_couple")),
                members=[name for name in names if name],
                score=household.get("score_summary", {}).get("published_score"),
                band=household.get("score_summary", {}).get("band"),
                voice_style=profile["style_key"],
                voice_label=profile["style_label"],
                voice_name=profile["voice_name"],
                gemini_voice=profile["gemini_voice"],
                openai_voice=profile["openai_voice"],
            )
        )

    return summaries
