"""The couple mode endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import (
    CaseContextDep,
    SettingsDep,
    ai_service_dependency,
    authorize_case,
)
from app.db.session import DbSession
from app.repositories import family_high_five_repository
from app.schemas.couple import (
    CoupleOverview,
    HighFiveItem,
    HighFiveRequest,
)
from app.services.couple_service import CoupleService

router = APIRouter(prefix="/api/cases/{case_id}", tags=["couple"])


@router.get("/couple", response_model=CoupleOverview)
async def get_couple(
    case_id: str,
    session: DbSession,
    context: CaseContextDep,
    settings: SettingsDep,
    ai_service=Depends(ai_service_dependency),
) -> CoupleOverview:
    """The portrait of the couple and the wall of their high fives."""
    case_id = authorize_case(case_id, settings)
    service = CoupleService(ai_service, context, model=settings.ai_copy_model)
    return await service.overview(session, case_id)


@router.post("/couple/high-five", response_model=HighFiveItem)
async def send_high_five(
    case_id: str,
    payload: HighFiveRequest,
    session: DbSession,
    settings: SettingsDep,
) -> HighFiveItem:
    """A high five between the two members of the household."""
    case_id = authorize_case(case_id, settings)
    high_five = family_high_five_repository.add_high_five(
        session,
        case_id,
        from_member=payload.from_member,
        to_member=payload.to_member,
        milestone_title=payload.milestone_title,
        message=payload.message,
    )
    session.commit()
    session.refresh(high_five)
    return HighFiveItem.model_validate(high_five)
