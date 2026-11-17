"""Milestone use cases."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.domain.enums import (
    VALID_STATUS_TRANSITIONS,
    FinancialProgressState,
    MilestoneStatus,
)
from app.domain.formatting import format_checkin_display
from app.errors import (
    InvalidStatusTransitionError,
    MilestoneNotFoundError,
)
from app.models.milestone import Milestone
from app.repositories import milestone_repository
from app.schemas.milestone import (
    CompleteMilestoneRequest,
    MilestoneListResponse,
    MilestoneResponse,
    SourceRefOut,
    StatusUpdateRequest,
    TaskProgressResponse,
    TaskResponse,
)


def to_response(milestone: Milestone) -> MilestoneResponse:
    """Convert a milestone into the shape the frontend consumes."""
    tasks = [
        TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            order=task.order_index,
            is_required=task.is_required,
            status=task.status,
            origin=task.origin,
            completed_at=task.completed_at,
        )
        for task in sorted(milestone.tasks, key=lambda t: (t.order_index, t.id))
    ]
    source = [
        SourceRefOut(
            part=ref.get("part", "financial-health"),
            section=ref.get("section"),
            json_path=ref.get("json_path"),
            quote=ref.get("quote"),
        )
        for ref in (milestone.source_refs or [])
        if isinstance(ref, dict)
    ]
    financial_progress = (
        float(milestone.financial_progress)
        if milestone.financial_progress is not None
        else None
    )
    return MilestoneResponse(
        id=milestone.id,
        title=milestone.title,
        why=milestone.why,
        action=milestone.action,
        section=milestone.section,
        status=milestone.status,
        checkin=format_checkin_display(milestone.checkin_next_date),
        case_id=milestone.case_id,
        category=milestone.category,
        type=milestone.type,
        priority=milestone.priority,
        tasks=tasks,
        task_progress=milestone.task_progress,
        financial_progress=financial_progress,
        financial_progress_state=milestone.financial_progress_state,
        financial_metric_key=milestone.financial_metric_key,
        financial_direction=milestone.financial_direction,
        financial_start_value=milestone.financial_start_value,
        financial_target_value=milestone.financial_target_value,
        financial_unit=milestone.financial_unit,
        financial_currency=milestone.financial_currency,
        due_date=milestone.due_date,
        checkin_pending=milestone.checkin_pending,
        checkin_date=milestone.checkin_next_date,
        overdue=milestone.overdue,
        source=source,
        created_at=milestone.created_at,
        updated_at=milestone.updated_at,
        completed_at=milestone.completed_at,
        last_reviewed_at=milestone.last_reviewed_at,
    )


def list_milestones(
    session: Session,
    case_id: str,
    *,
    status: str | None = None,
    category: str | None = None,
    milestone_type: str | None = None,
    priority: str | None = None,
) -> list[Milestone]:
    """The milestones of a case."""
    return milestone_repository.list_milestones(
        session,
        case_id,
        status=status,
        category=category,
        milestone_type=milestone_type,
        priority=priority,
    )


def build_list_response(
    milestones: list[Milestone],
    *,
    case_id: str,
    meta=None,
    group_by_category: bool = False,
) -> MilestoneListResponse:
    """The listing response, optionally grouped by category."""
    responses = [to_response(milestone) for milestone in milestones]
    grouped: dict[str, list[MilestoneResponse]] | None = None
    if group_by_category:
        grouped = {}
        for response in responses:
            grouped.setdefault(response.category, []).append(response)
    return MilestoneListResponse(
        milestones=responses, meta=meta, grouped_by_category=grouped
    )


def get_milestone(
    session: Session, case_id: str, milestone_id: str
) -> Milestone:
    """One milestone of a case."""
    milestone = milestone_repository.get_milestone_for_case(
        session, case_id, milestone_id
    )
    if milestone is None:
        raise MilestoneNotFoundError(
            f"Milestone {milestone_id} does not exist for this case"
        )
    return milestone


def update_status(
    session: Session,
    case_id: str,
    milestone_id: str,
    payload: StatusUpdateRequest,
) -> Milestone:
    """Move a milestone to another status.

    Only the client changes the status, and only along the allowed
    transitions.
    """
    milestone = get_milestone(session, case_id, milestone_id)
    current = MilestoneStatus(milestone.status)
    target = payload.status
    if target is current:
        return milestone
    if target not in VALID_STATUS_TRANSITIONS.get(current, set()):
        raise InvalidStatusTransitionError(
            f"A milestone cannot go from {current.value} to {target.value}",
            details={"from": current.value, "to": target.value},
        )
    milestone.status = target.value
    if target is MilestoneStatus.COMPLETED:
        milestone.completed_at = datetime.now(UTC)
    elif target is MilestoneStatus.IN_PROGRESS and current is MilestoneStatus.COMPLETED:
        milestone.completed_at = None
    session.flush()
    return milestone


def complete_milestone(
    session: Session,
    case_id: str,
    milestone_id: str,
    payload: CompleteMilestoneRequest,
) -> Milestone:
    """Close a milestone on the client's explicit confirmation."""
    milestone = get_milestone(session, case_id, milestone_id)
    if not payload.confirmed:
        raise InvalidStatusTransitionError(
            "Completing a milestone needs an explicit confirmation",
            details={"confirmed": False},
        )
    current = MilestoneStatus(milestone.status)
    if current is MilestoneStatus.CANCELLED:
        raise InvalidStatusTransitionError(
            "A cancelled milestone cannot be completed",
            details={"from": current.value, "to": "completed"},
        )
    if current is MilestoneStatus.COMPLETED:
        return milestone
    milestone.status = MilestoneStatus.COMPLETED.value
    milestone.completed_at = datetime.now(UTC)
    session.flush()
    return milestone


def get_progress(
    session: Session, case_id: str, milestone_id: str
) -> TaskProgressResponse:
    """The operational progress of a milestone."""
    milestone = get_milestone(session, case_id, milestone_id)
    required = [task for task in milestone.tasks if task.is_required]
    optional = [task for task in milestone.tasks if not task.is_required]
    from app.domain.completion import should_auto_complete

    return TaskProgressResponse(
        milestone_id=milestone.id,
        task_progress=milestone.task_progress,
        required_tasks=len(required),
        completed_required_tasks=len(
            [task for task in required if task.status == "completed"]
        ),
        optional_tasks=len(optional),
        completed_optional_tasks=len(
            [task for task in optional if task.status == "completed"]
        ),
        auto_completable=should_auto_complete(
            milestone_type=milestone.type,
            status=milestone.status,
            tasks=list(milestone.tasks),
        ),
    )


def set_financial_progress_state(
    milestone: Milestone, state: FinancialProgressState
) -> None:
    """Store the financial progress state on the milestone."""
    milestone.financial_progress_state = state.value
