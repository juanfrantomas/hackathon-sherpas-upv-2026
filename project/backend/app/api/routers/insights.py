"""The proactive mentor and the translator of jargon."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import (
    CaseContextDep,
    SettingsDep,
    ai_service_dependency,
    authorize_case,
)
from app.db.session import DbSession
from app.schemas.simulator import MentorInsightsResponse
from app.services.insights_service import InsightsService

router = APIRouter(prefix="/api/cases/{case_id}", tags=["mentor"])


@router.get("/mentor/insights", response_model=MentorInsightsResponse)
async def get_mentor_insights(
    case_id: str,
    session: DbSession,
    context: CaseContextDep,
    settings: SettingsDep,
    ai_service=Depends(ai_service_dependency),
) -> MentorInsightsResponse:
    """The nudge of the mentor and the jargon pills of the household."""
    case_id = authorize_case(case_id, settings)
    service = InsightsService(ai_service, context, model=settings.ai_copy_model)
    return await service.insights(case_id)
