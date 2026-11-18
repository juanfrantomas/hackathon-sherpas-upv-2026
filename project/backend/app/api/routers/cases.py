"""The catalogue of the households."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import case_source_dependency, settings_dependency
from app.integration.mcp.context import CaseContext
from app.schemas.case import CaseSummary
from app.services.case_directory_service import list_cases

router = APIRouter(prefix="/api", tags=["cases"])


@router.get("/cases", response_model=list[CaseSummary])
async def get_cases(
    settings=Depends(settings_dependency),
    case_source=Depends(case_source_dependency),
) -> list[CaseSummary]:
    """The households this instance can serve, with their voice profile."""
    allowed = settings.allowed_case_id_set
    context = CaseContext(case_source)
    summaries = await list_cases(case_source, context)
    if not allowed:
        return []
    return [summary for summary in summaries if summary.case_id in allowed]
