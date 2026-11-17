"""The financial story endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import (
    CaseContextDep,
    SettingsDep,
    ai_service_dependency,
    authorize_case,
)
from app.db.session import DbSession
from app.schemas.couple import StoryResponse
from app.services.story_service import StoryService

router = APIRouter(prefix="/api/cases/{case_id}", tags=["story"])


@router.get("/story", response_model=StoryResponse)
async def get_story(
    case_id: str,
    session: DbSession,
    context: CaseContextDep,
    settings: SettingsDep,
    ai_service=Depends(ai_service_dependency),
) -> StoryResponse:
    """The four scenes of the financial story of a household."""
    case_id = authorize_case(case_id, settings)
    service = StoryService(ai_service, context, model=settings.ai_copy_model)
    return await service.story(case_id)
