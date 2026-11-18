"""Check-in use cases: scheduling reviews and registering them."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.domain.enums import CheckinStatus, MilestoneStatus
from app.domain.formatting import format_checkin_display
from app.domain.recurrence import (
    is_checkin_pending,
    is_overdue,
    next_review_date,
)
from app.errors import InvalidStatusTransitionError
from app.models.checkin import MilestoneCheckin
from app.models.milestone import Milestone
from app.repositories import checkin_repository
from app.schemas.checkin import (
    CheckinListResponse,
    CheckinResponse,
    MilestoneCheckinResponse,
    ReviewCompletedResponse,
)


def _new_checkin_id() -> str:
    return f"chk_{uuid.uuid4().hex[:16]}"


def refresh_indicators(
    session: Session, milestone: Milestone, *, today: date | None = None
) -> None:
    """Recompute the derived indicators of a milestone."""
    today = today or datetime.now(UTC).date()
    milestone.checkin_pending = is_checkin_pending(
        scheduled_date=milestone.checkin_next_date,
        status=milestone.status,
        today=today,
    )
    milestone.overdue = is_overdue(
        due_date=milestone.due_date, status=milestone.status, today=today
    )
    session.flush()


def list_case_checkins(
    session: Session, case_id: str, *, pending_only: bool = False
) -> CheckinListResponse:
    """The reviews of a case."""
    rows = checkin_repository.list_case_checkins(
        session, case_id, pending_only=pending_only
    )
    today = datetime.now(UTC).date()
    responses: list[CheckinResponse] = []
    for checkin, title in rows:
        pending = (
            checkin.status == CheckinStatus.SCHEDULED.value
            and checkin.scheduled_date < today
        )
        responses.append(
            CheckinResponse(
                id=checkin.id,
                milestone_id=checkin.milestone_id,
                title=title,
                scheduled_date=checkin.scheduled_date,
                effective_date=checkin.effective_date,
                status=checkin.status,
                completed_at=checkin.completed_at,
                pending=pending,
                note=checkin.note,
            )
        )
    return CheckinListResponse(checkins=responses)


def get_milestone_schedule(
    session: Session, milestone: Milestone
) -> MilestoneCheckinResponse:
    """The review schedule of one milestone."""
    history = [
        CheckinResponse(
            id=checkin.id,
            milestone_id=checkin.milestone_id,
            title=milestone.title,
            scheduled_date=checkin.scheduled_date,
            effective_date=checkin.effective_date,
            status=checkin.status,
            completed_at=checkin.completed_at,
            pending=checkin.status == CheckinStatus.SCHEDULED.value
            and checkin.scheduled_date < datetime.now(UTC).date(),
            note=checkin.note,
        )
        for checkin in checkin_repository.list_checkins(session, milestone.id)
    ]
    return MilestoneCheckinResponse(
        milestone_id=milestone.id,
        next_review=milestone.checkin_next_date,
        next_review_display=format_checkin_display(milestone.checkin_next_date),
        pending=milestone.checkin_pending,
        overdue=milestone.overdue,
        last_reviewed_at=milestone.last_reviewed_at,
        history=history,
    )


def complete_review(
    session: Session,
    milestone: Milestone,
    *,
    effective_date: date | None = None,
    note: str | None = None,
    today: date | None = None,
) -> ReviewCompletedResponse:
    """Register that a review happened and schedule the next one.

    The date the review was *planned* for is kept, the date it actually
    happened is stored next to it, the pending review is resolved and the
    next monthly review is scheduled with a deterministic rule.
    """
    today = today or datetime.now(UTC).date()
    if effective_date is None:
        effective_date = today
    if effective_date > today:
        raise InvalidStatusTransitionError(
            "A review cannot be dated in the future",
            details={"effective_date": effective_date.isoformat()},
        )
    if milestone.status == MilestoneStatus.CANCELLED.value:
        raise InvalidStatusTransitionError(
            "A cancelled milestone does not have reviews"
        )

    scheduled = milestone.checkin_next_date or effective_date

    # The same review reported twice is the same review: nothing moves.
    already = checkin_repository.get_completed_checkin_by_effective_date(
        session, milestone.id, effective_date
    )
    if already is not None:
        next_review = milestone.checkin_next_date
        return ReviewCompletedResponse(
            checkin=CheckinResponse(
                id=already.id,
                milestone_id=already.milestone_id,
                title=milestone.title,
                scheduled_date=already.scheduled_date,
                effective_date=already.effective_date,
                status=already.status,
                completed_at=already.completed_at,
                pending=False,
                note=already.note,
            ),
            next_review=next_review,
            next_review_display=format_checkin_display(next_review),
            pending=milestone.checkin_pending,
        )

    existing = checkin_repository.get_checkin(session, milestone.id, scheduled)

    if existing is not None and existing.status == CheckinStatus.COMPLETED.value:
        # Already registered: idempotent, nothing else to do.
        next_review = milestone.checkin_next_date
        return ReviewCompletedResponse(
            checkin=CheckinResponse(
                id=existing.id,
                milestone_id=existing.milestone_id,
                title=milestone.title,
                scheduled_date=existing.scheduled_date,
                effective_date=existing.effective_date,
                status=existing.status,
                completed_at=existing.completed_at,
                pending=False,
                note=existing.note,
            ),
            next_review=next_review,
            next_review_display=format_checkin_display(next_review),
            pending=milestone.checkin_pending,
        )

    if existing is None:
        existing = MilestoneCheckin(
            id=_new_checkin_id(),
            milestone_id=milestone.id,
            scheduled_date=scheduled,
            status=CheckinStatus.SCHEDULED.value,
        )
        checkin_repository.add_checkin(session, existing)
    existing.status = CheckinStatus.COMPLETED.value
    existing.effective_date = effective_date
    existing.completed_at = datetime.now(UTC)
    if note:
        existing.note = note
    session.flush()

    # The next review is anchored on the planned date, then pushed forward
    # until it is not in the past.
    next_scheduled = next_review_date(scheduled, today=today)
    upcoming = checkin_repository.get_checkin(session, milestone.id, next_scheduled)
    if upcoming is None:
        checkin_repository.add_checkin(
            session,
            MilestoneCheckin(
                id=_new_checkin_id(),
                milestone_id=milestone.id,
                scheduled_date=next_scheduled,
                status=CheckinStatus.SCHEDULED.value,
            ),
        )

    milestone.checkin_next_date = next_scheduled
    milestone.checkin_pending = False
    milestone.last_reviewed_at = datetime.now(UTC)
    session.flush()

    return ReviewCompletedResponse(
        checkin=CheckinResponse(
            id=existing.id,
            milestone_id=existing.milestone_id,
            title=milestone.title,
            scheduled_date=existing.scheduled_date,
            effective_date=existing.effective_date,
            status=existing.status,
            completed_at=existing.completed_at,
            pending=False,
            note=existing.note,
        ),
        next_review=next_scheduled,
        next_review_display=format_checkin_display(next_scheduled),
        pending=False,
    )


def schedule_first_checkin(
    session: Session, milestone: Milestone, *, scheduled: date
) -> None:
    """Plan the first review of a milestone."""
    milestone.checkin_next_date = scheduled
    milestone.checkin_interval_months = 1
    if checkin_repository.get_checkin(session, milestone.id, scheduled) is None:
        checkin_repository.add_checkin(
            session,
            MilestoneCheckin(
                id=_new_checkin_id(),
                milestone_id=milestone.id,
                scheduled_date=scheduled,
                status=CheckinStatus.SCHEDULED.value,
            ),
        )
    session.flush()
