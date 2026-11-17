"""Persistence for scheduled reviews."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.checkin import MilestoneCheckin


def list_checkins(session: Session, milestone_id: str) -> list[MilestoneCheckin]:
    """The review history of a milestone."""
    return list(
        session.scalars(
            select(MilestoneCheckin)
            .where(MilestoneCheckin.milestone_id == milestone_id)
            .order_by(MilestoneCheckin.scheduled_date.asc())
        )
    )


def get_checkin(
    session: Session, milestone_id: str, scheduled_date: date
) -> MilestoneCheckin | None:
    """The review planned for a given date."""
    return session.scalars(
        select(MilestoneCheckin).where(
            MilestoneCheckin.milestone_id == milestone_id,
            MilestoneCheckin.scheduled_date == scheduled_date,
        )
    ).first()


def get_completed_checkin_by_effective_date(
    session: Session, milestone_id: str, effective_date: date
) -> MilestoneCheckin | None:
    """The review that was already registered for a given day."""
    return session.scalars(
        select(MilestoneCheckin).where(
            MilestoneCheckin.milestone_id == milestone_id,
            MilestoneCheckin.effective_date == effective_date,
            MilestoneCheckin.status == "completed",
        )
    ).first()


def add_checkin(session: Session, checkin: MilestoneCheckin) -> MilestoneCheckin:
    """Store a review."""
    session.add(checkin)
    return checkin


def list_case_checkins(
    session: Session, case_id: str, *, pending_only: bool = False
) -> list[tuple[MilestoneCheckin, str]]:
    """The reviews of a case, with the title of their milestone."""
    from app.models.milestone import Milestone

    query = (
        select(MilestoneCheckin, Milestone.title)
        .join(Milestone, Milestone.id == MilestoneCheckin.milestone_id)
        .where(Milestone.case_id == case_id)
    )
    if pending_only:
        query = query.where(
            MilestoneCheckin.status == "scheduled",
            Milestone.status.notin_(["completed", "cancelled"]),
        )
    query = query.order_by(MilestoneCheckin.scheduled_date.asc())
    return [(row[0], row[1]) for row in session.execute(query)]
