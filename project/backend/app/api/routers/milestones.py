"""Milestone endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query

from app.api.deps import (
    ai_service_dependency,
    authorize_case,
    case_source_dependency,
    settings_dependency,
)
from app.db.session import DbSession
from app.domain.enums import SyncTrigger
from app.errors import AppError
from app.repositories import milestone_repository, notification_repository
from app.schemas.common import MilestoneListMeta, ProgressSummary
from app.schemas.milestone import (
    CompleteMilestoneRequest,
    MilestoneListResponse,
    MilestoneResponse,
    StatusUpdateRequest,
    TaskProgressResponse,
)
from app.services import (
    case_service,
    generation_service,
    milestone_service,
    notification_service,
)

router = APIRouter(prefix="/api/cases/{case_id}", tags=["milestones"])


def _meta(session, case_id: str, settings, case_source) -> MilestoneListMeta:
    """Context about the state of the data behind the listing."""
    state = notification_repository.get_sync_state(session, case_id)
    stale = False
    reason: str | None = None
    last_success = state.last_success_at if state else None

    if state is not None and state.status == "error":
        stale = True
        reason = state.last_error_code or "SYNC_ERROR"
    elif getattr(case_source, "last_error", None):
        stale = True
        reason = case_source.last_error
    elif (
        settings.case_source == "auto"
        and getattr(case_source, "data_source", "") == "local"
    ):
        stale = True
        reason = "MCP_UNAVAILABLE"

    return MilestoneListMeta(
        case_id=case_id,
        count=0,
        stale=stale,
        stale_reason=reason,
        data_source=getattr(case_source, "data_source", None),
        last_successful_sync_at=last_success,
    )


async def _ensure_milestones(
    session,
    case_id: str,
    settings,
    case_source,
    ai_service,
) -> None:
    """Generate the milestones the first time a case is opened."""
    if milestone_repository.count_milestones(session, case_id) > 0:
        return
    if not settings.auto_generate_on_first_access:
        return
    if not settings.ai_generation_enabled:
        return

    digest = await case_service.get_digest(case_source, case_id)
    case_service.ensure_case(
        session, case_id, digest, data_source=getattr(case_source, "data_source", "mcp")
    )
    await generation_service.generate_milestones(session, case_id, digest, ai_service)
    state = notification_repository.get_or_create_sync_state(session, case_id)
    state.status = "success"
    state.plan_fingerprint = digest.fingerprint
    state.last_success_at = datetime.now(UTC)
    state.trigger = SyncTrigger.FIRST_ACCESS.value
    session.commit()


@router.get("/milestones", response_model=MilestoneListResponse)
async def list_milestones(
    case_id: str,
    session: DbSession,
    group_by: str = Query("none", pattern="^(none|category)$"),
    status_filter: str | None = Query(None, alias="status"),
    category: str | None = Query(None),
    milestone_type: str | None = Query(None, alias="type"),
    priority: str | None = Query(None),
    settings=Depends(settings_dependency),
    case_source=Depends(case_source_dependency),
    ai_service=Depends(ai_service_dependency),
) -> MilestoneListResponse:
    """The milestones of a case, in the shape the frontend consumes."""
    case_id = authorize_case(case_id, settings)
    await _ensure_milestones(session, case_id, settings, case_source, ai_service)

    milestones = milestone_service.list_milestones(
        session,
        case_id,
        status=status_filter,
        category=category,
        milestone_type=milestone_type,
        priority=priority,
    )
    notification_service.evaluate(session, case_id)
    session.commit()

    meta = _meta(session, case_id, settings, case_source)
    meta.count = len(milestones)
    return milestone_service.build_list_response(
        milestones,
        case_id=case_id,
        meta=meta,
        group_by_category=group_by == "category",
    )


@router.get("/milestones/{milestone_id}", response_model=MilestoneResponse)
async def get_milestone(
    case_id: str,
    milestone_id: str,
    session: DbSession,
    settings=Depends(settings_dependency),
) -> MilestoneResponse:
    """One milestone of a case."""
    case_id = authorize_case(case_id, settings)
    milestone = milestone_service.get_milestone(session, case_id, milestone_id)
    return milestone_service.to_response(milestone)


@router.patch("/milestones/{milestone_id}/status", response_model=MilestoneResponse)
async def update_milestone_status(
    case_id: str,
    milestone_id: str,
    payload: StatusUpdateRequest,
    session: DbSession,
    settings=Depends(settings_dependency),
) -> MilestoneResponse:
    """Move a milestone to another status.  Only the client does this."""
    case_id = authorize_case(case_id, settings)
    milestone = milestone_service.update_status(session, case_id, milestone_id, payload)
    session.commit()
    session.refresh(milestone)
    return milestone_service.to_response(milestone)


@router.post("/milestones/{milestone_id}/complete", response_model=MilestoneResponse)
async def complete_milestone(
    case_id: str,
    milestone_id: str,
    payload: CompleteMilestoneRequest,
    session: DbSession,
    settings=Depends(settings_dependency),
) -> MilestoneResponse:
    """Close a milestone on the client's explicit confirmation."""
    case_id = authorize_case(case_id, settings)
    milestone = milestone_service.complete_milestone(
        session, case_id, milestone_id, payload
    )
    session.commit()
    session.refresh(milestone)
    return milestone_service.to_response(milestone)


@router.get(
    "/milestones/{milestone_id}/progress", response_model=TaskProgressResponse
)
async def get_milestone_progress(
    case_id: str,
    milestone_id: str,
    session: DbSession,
    settings=Depends(settings_dependency),
) -> TaskProgressResponse:
    """The operational progress of a milestone."""
    case_id = authorize_case(case_id, settings)
    return milestone_service.get_progress(session, case_id, milestone_id)


@router.post("/milestones/generate", response_model=MilestoneListResponse)
async def generate_milestones(
    case_id: str,
    session: DbSession,
    payload: dict | None = None,
    settings=Depends(settings_dependency),
    case_source=Depends(case_source_dependency),
    ai_service=Depends(ai_service_dependency),
) -> MilestoneListResponse:
    """Generate the milestones of a case."""
    case_id = authorize_case(case_id, settings)
    if not settings.ai_generation_enabled:
        raise AppError(
            "The generation of milestones is disabled on this instance",
            code="GENERATION_DISABLED",
            status_code=503,
        )
    force = bool((payload or {}).get("force"))
    if milestone_repository.count_milestones(session, case_id) > 0 and not force:
        raise AppError(
            "This case already has milestones; use force to regenerate them",
            code="SYNC_CONFLICT",
            status_code=409,
        )

    digest = await case_service.get_digest(case_source, case_id)
    case_service.ensure_case(
        session, case_id, digest, data_source=getattr(case_source, "data_source", "mcp")
    )
    await generation_service.generate_milestones(session, case_id, digest, ai_service)
    state = notification_repository.get_or_create_sync_state(session, case_id)
    state.status = "success"
    state.plan_fingerprint = digest.fingerprint
    state.last_success_at = datetime.now(UTC)
    state.trigger = SyncTrigger.MANUAL.value
    session.commit()

    milestones = milestone_service.list_milestones(session, case_id)
    meta = _meta(session, case_id, settings, case_source)
    meta.count = len(milestones)
    return milestone_service.build_list_response(milestones, case_id=case_id, meta=meta)


@router.get("/progress", response_model=ProgressSummary)
async def get_case_progress(
    case_id: str,
    session: DbSession,
    settings=Depends(settings_dependency),
) -> ProgressSummary:
    """The aggregated progress of a case."""
    case_id = authorize_case(case_id, settings)
    from app.domain.progress import average_task_progress

    milestones = milestone_repository.list_milestones(session, case_id)
    counts = milestone_repository.status_counts(session, case_id)
    task_values = [m.task_progress for m in milestones]
    financial_values = [
        float(m.financial_progress)
        for m in milestones
        if m.financial_progress is not None
    ]
    financial_average = (
        round(sum(financial_values) / len(financial_values), 2)
        if financial_values
        else None
    )
    return ProgressSummary(
        milestones_total=len(milestones),
        completed=counts.get("completed", 0),
        in_progress=counts.get("in_progress", 0),
        not_started=counts.get("not_started", 0),
        on_hold=counts.get("on_hold", 0),
        cancelled=counts.get("cancelled", 0),
        overdue=len([m for m in milestones if m.overdue]),
        checkins_pending=len([m for m in milestones if m.checkin_pending]),
        task_progress_average=average_task_progress(task_values),
        financial_progress_average=financial_average,
    )
