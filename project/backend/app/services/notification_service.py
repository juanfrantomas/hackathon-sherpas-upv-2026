"""Notification use cases.

The generator is deterministic: a pending review or an overdue milestone
always produces the same notice, and the dedupe key makes sure it is only
stored once.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.domain.enums import NotificationType
from app.models.milestone import Milestone
from app.models.notification import Notification
from app.repositories import milestone_repository, notification_repository
from app.schemas.checkin import (
    MarkReadResponse,
    NotificationListResponse,
    NotificationResponse,
)


def _new_notification_id() -> str:
    return f"ntf_{uuid.uuid4().hex[:16]}"


def _dedupe_key(case_id: str, milestone_id: str, kind: str, reference: date | None) -> str:
    reference_part = reference.isoformat() if reference else "none"
    return f"{case_id}:{milestone_id}:{kind}:{reference_part}"


def evaluate(session: Session, case_id: str, *, today: date | None = None) -> int:
    """Create the notices that are due for a case.

    Called when the milestones are read, after a synchronisation and by the
    background scheduler, so a notice appears even when nobody had the app
    open.
    """
    today = today or datetime.now(UTC).date()
    created = 0

    for milestone in milestone_repository.list_milestones(session, case_id):
        if milestone.checkin_pending:
            notice = Notification(
                id=_new_notification_id(),
                case_id=case_id,
                milestone_id=milestone.id,
                type=NotificationType.CHECKIN_PENDING.value,
                dedupe_key=_dedupe_key(
                    case_id, milestone.id, "checkin_pending", milestone.checkin_next_date
                ),
                title="A review is waiting for you",
                body=(
                    f"\"{milestone.title}\" was scheduled for review on "
                    f"{milestone.checkin_next_date.isoformat() if milestone.checkin_next_date else 'an earlier date'}."
                ),
                reference_date=milestone.checkin_next_date,
            )
            if notification_repository.add_notification(session, notice) is notice:
                created += 1

        if milestone.overdue:
            notice = Notification(
                id=_new_notification_id(),
                case_id=case_id,
                milestone_id=milestone.id,
                type=NotificationType.OVERDUE.value,
                dedupe_key=_dedupe_key(
                    case_id, milestone.id, "overdue", milestone.due_date
                ),
                title="A milestone passed its target date",
                body=(
                    f"\"{milestone.title}\" was due on "
                    f"{milestone.due_date.isoformat() if milestone.due_date else 'an earlier date'} "
                    "and is still open."
                ),
                reference_date=milestone.due_date,
            )
            if notification_repository.add_notification(session, notice) is notice:
                created += 1

    session.flush()
    return created


def list_notifications(
    session: Session,
    case_id: str,
    *,
    unread_only: bool = False,
    notification_type: str | None = None,
) -> NotificationListResponse:
    """The notices of a case."""
    rows = notification_repository.list_notifications(
        session, case_id, unread_only=unread_only, notification_type=notification_type
    )
    return NotificationListResponse(
        notifications=[
            NotificationResponse(
                id=notice.id,
                case_id=notice.case_id,
                milestone_id=notice.milestone_id,
                type=notice.type,
                title=notice.title,
                body=notice.body,
                reference_date=notice.reference_date,
                created_at=notice.created_at,
                read_at=notice.read_at,
            )
            for notice in rows
        ],
        unread_count=notification_repository.count_unread(session, case_id),
    )


def mark_read(
    session: Session, case_id: str, notification_id: str
) -> NotificationResponse:
    """Mark one notice as read."""
    notice = notification_repository.get_notification(
        session, case_id, notification_id
    )
    if notice is None:
        from app.errors import AppError

        raise AppError(
            f"Notification {notification_id} does not exist",
            code="NOTIFICATION_NOT_FOUND",
            status_code=404,
        )
    notification_repository.mark_read(session, notice)
    session.flush()
    return NotificationResponse(
        id=notice.id,
        case_id=notice.case_id,
        milestone_id=notice.milestone_id,
        type=notice.type,
        title=notice.title,
        body=notice.body,
        reference_date=notice.reference_date,
        created_at=notice.created_at,
        read_at=notice.read_at,
    )


def mark_all_read(session: Session, case_id: str) -> MarkReadResponse:
    """Mark every notice of a case as read."""
    count = notification_repository.mark_all_read(session, case_id)
    session.flush()
    return MarkReadResponse(read=count)


def milestones_with_notices(session: Session, case_id: str) -> list[Milestone]:
    """Helper used by the scheduler to refresh the indicators of a case."""
    return milestone_repository.list_milestones(session, case_id)
