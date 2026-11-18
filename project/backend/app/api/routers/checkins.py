"""Check-in endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import authorize_case, settings_dependency
from app.db.session import DbSession
from app.schemas.checkin import (
    CheckinListResponse,
    MilestoneCheckinResponse,
    ReviewCompletedRequest,
    ReviewCompletedResponse,
)
from app.services import checkin_service, milestone_service

router = APIRouter(prefix="/api/cases/{case_id}", tags=["checkins"])


@router.get("/checkins", response_model=CheckinListResponse)
async def list_checkins(
    case_id: str,
    session: DbSession,
    pending: bool = Query(False),
    settings=Depends(settings_dependency),
) -> CheckinListResponse:
    """The reviews of a case."""
    case_id = authorize_case(case_id, settings)
    return checkin_service.list_case_checkins(session, case_id, pending_only=pending)


@router.get(
    "/milestones/{milestone_id}/checkins", response_model=MilestoneCheckinResponse
)
async def get_milestone_checkins(
    case_id: str,
    milestone_id: str,
    session: DbSession,
    settings=Depends(settings_dependency),
) -> MilestoneCheckinResponse:
    """The review schedule of one milestone."""
    case_id = authorize_case(case_id, settings)
    milestone = milestone_service.get_milestone(session, case_id, milestone_id)
    return checkin_service.get_milestone_schedule(session, milestone)


@router.post(
    "/milestones/{milestone_id}/checkins/complete",
    response_model=ReviewCompletedResponse,
)
async def complete_review(
    case_id: str,
    milestone_id: str,
    payload: ReviewCompletedRequest,
    session: DbSession,
    settings=Depends(settings_dependency),
) -> ReviewCompletedResponse:
    """Register that a review happened and schedule the next one."""
    case_id = authorize_case(case_id, settings)
    milestone = milestone_service.get_milestone(session, case_id, milestone_id)
    response = checkin_service.complete_review(
        session, milestone, effective_date=payload.effective_date, note=payload.note
    )
    session.commit()
    return response
