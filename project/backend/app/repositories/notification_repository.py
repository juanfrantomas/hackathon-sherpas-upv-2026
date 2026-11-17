"""Persistence for notifications and synchronisation state."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.sync_state import SyncState


def add_notification(session: Session, notification: Notification) -> Notification:
    """Store a notification, ignoring duplicates."""
    existing = session.scalars(
        select(Notification).where(Notification.dedupe_key == notification.dedupe_key)
    ).first()
    if existing is not None:
        return existing
    session.add(notification)
    return notification


def list_notifications(
    session: Session,
    case_id: str,
    *,
    unread_only: bool = False,
    notification_type: str | None = None,
) -> list[Notification]:
    """The notifications of a case."""
    query = select(Notification).where(Notification.case_id == case_id)
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    if notification_type:
        query = query.where(Notification.type == notification_type)
    query = query.order_by(Notification.created_at.desc())
    return list(session.scalars(query))


def count_unread(session: Session, case_id: str) -> int:
    """How many notifications are still unread."""
    from sqlalchemy import func

    return int(
        session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.case_id == case_id, Notification.read_at.is_(None))
        )
        or 0
    )


def get_notification(session: Session, case_id: str, notification_id: str) -> Notification | None:
    """One notification of a case."""
    return session.scalars(
        select(Notification).where(
            Notification.id == notification_id, Notification.case_id == case_id
        )
    ).first()


def mark_read(session: Session, notification: Notification) -> Notification:
    """Mark a notification as read (idempotent)."""
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
    return notification


def mark_all_read(session: Session, case_id: str) -> int:
    """Mark every notification of a case as read."""
    now = datetime.now(UTC)
    count = 0
    for notification in list_notifications(session, case_id, unread_only=True):
        notification.read_at = now
        count += 1
    return count


def get_sync_state(session: Session, case_id: str) -> SyncState | None:
    """The synchronisation state of a case."""
    return session.scalars(
        select(SyncState).where(SyncState.case_id == case_id)
    ).first()


def get_or_create_sync_state(session: Session, case_id: str) -> SyncState:
    """The synchronisation state of a case, created on demand."""
    state = get_sync_state(session, case_id)
    if state is None:
        state = SyncState(id=f"sync_{case_id}", case_id=case_id, status="idle")
        session.add(state)
        session.flush()
    return state


def claim_sync(session: Session, case_id: str) -> bool:
    """Try to become the one running synchronisation for a case.

    Returns ``False`` when another synchronisation is already running, which
    the API turns into a ``409``.
    """
    state = get_or_create_sync_state(session, case_id)
    if state.status == "running":
        return False
    state.status = "running"
    state.last_attempt_at = datetime.now(UTC)
    session.flush()
    return True
