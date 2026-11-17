"""Synchronisation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import (
    ai_service_dependency,
    authorize_case,
    case_source_dependency,
    settings_dependency,
)
from app.db.session import DbSession
from app.repositories import notification_repository
from app.schemas.common import MilestoneListMeta
from app.schemas.milestone import MilestoneListResponse
from app.services import milestone_service, sync_service

router = APIRouter(prefix="/api/cases/{case_id}", tags=["sync"])


class SyncRequest(BaseModel):
    """A manual synchronisation request."""

    force: bool = Field(
        default=False, description="Ignore the interval and the fingerprint"
    )


class SyncStateResponse(BaseModel):
    """The synchronisation state of a case."""

    case_id: str
    status: str
    trigger: str | None = None
    plan_fingerprint: str | None = None
    last_attempt_at: str | None = None
    last_success_at: str | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    milestones_created: int = 0
    milestones_updated: int = 0
    milestones_kept: int = 0
    ai_model: str | None = None


@router.get("/sync", response_model=SyncStateResponse)
async def get_sync_state(
    case_id: str,
    session: DbSession,
    settings=Depends(settings_dependency),
) -> SyncStateResponse:
    """The state of the last synchronisation."""
    case_id = authorize_case(case_id, settings)
    from app.services.case_service import ensure_case_row

    ensure_case_row(session, case_id)
    state = notification_repository.get_or_create_sync_state(session, case_id)
    session.commit()
    return SyncStateResponse(
        case_id=case_id,
        status=state.status,
        trigger=state.trigger,
        plan_fingerprint=state.plan_fingerprint,
        last_attempt_at=state.last_attempt_at.isoformat() if state.last_attempt_at else None,
        last_success_at=state.last_success_at.isoformat() if state.last_success_at else None,
        last_error_code=state.last_error_code,
        last_error_message=state.last_error_message,
        milestones_created=state.milestones_created,
        milestones_updated=state.milestones_updated,
        milestones_kept=state.milestones_kept,
        ai_model=state.ai_model,
    )


@router.post("/sync", response_model=MilestoneListResponse)
async def sync_case(
    case_id: str,
    session: DbSession,
    payload: SyncRequest | None = None,
    settings=Depends(settings_dependency),
    case_source=Depends(case_source_dependency),
    ai_service=Depends(ai_service_dependency),
) -> MilestoneListResponse:
    """Bring the milestones in line with the current plan."""
    case_id = authorize_case(case_id, settings)
    force = bool(payload.force) if payload else False
    summary = await sync_service.sync_case(
        session,
        case_id,
        case_source,
        ai_service,
        settings,
        trigger="manual",
        force=force,
    )
    session.commit()

    milestones = milestone_service.list_milestones(session, case_id)
    state = notification_repository.get_sync_state(session, case_id)
    meta = MilestoneListMeta(
        case_id=case_id,
        count=len(milestones),
        stale=False,
        stale_reason=None if summary.changed else summary.reason,
        data_source=getattr(case_source, "data_source", None),
        last_successful_sync_at=state.last_success_at if state else None,
    )
    return milestone_service.build_list_response(
        milestones, case_id=case_id, meta=meta
    )
