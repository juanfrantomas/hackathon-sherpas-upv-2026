"""Persistence for milestones and their tasks."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import MilestoneStatus
from app.models.milestone import Milestone
from app.models.task import MilestoneTask


def _base_query() -> Select[Any]:
    return select(Milestone).options(
        selectinload(Milestone.tasks),
    )


def list_milestones(
    session: Session,
    case_id: str,
    *,
    status: str | None = None,
    category: str | None = None,
    milestone_type: str | None = None,
    priority: str | None = None,
    include_stale: bool = True,
) -> list[Milestone]:
    """The milestones of a case, with their tasks loaded."""
    query = _base_query().where(Milestone.case_id == case_id)
    if status:
        query = query.where(Milestone.status == status)
    if category:
        query = query.where(Milestone.category == category)
    if milestone_type:
        query = query.where(Milestone.type == milestone_type)
    if priority:
        query = query.where(Milestone.priority == priority)
    if not include_stale:
        query = query.where(Milestone.is_stale.is_(False))
    query = query.order_by(
        Milestone.priority_rank.asc(),
        Milestone.created_at.asc(),
        Milestone.id.asc(),
    )
    return list(session.scalars(query))


def get_milestone(session: Session, milestone_id: str) -> Milestone | None:
    """One milestone with its tasks."""
    return session.scalars(
        _base_query().where(Milestone.id == milestone_id)
    ).first()  # type: ignore[return-value]


def get_milestone_for_case(
    session: Session, case_id: str, milestone_id: str
) -> Milestone | None:
    """One milestone, scoped to its case."""
    return session.scalars(
        _base_query().where(Milestone.id == milestone_id, Milestone.case_id == case_id)
    ).first()  # type: ignore[return-value]


def get_milestone_by_stable_key(
    session: Session, case_id: str, stable_key: str
) -> Milestone | None:
    """The milestone of a case with a given stable key."""
    return session.scalars(
        select(Milestone).where(
            Milestone.case_id == case_id, Milestone.stable_key == stable_key
        )
    ).first()


def add_milestone(session: Session, milestone: Milestone) -> Milestone:
    """Store a new milestone."""
    session.add(milestone)
    return milestone


def count_milestones(session: Session, case_id: str) -> int:
    """How many milestones a case has."""
    from sqlalchemy import func

    return int(
        session.scalar(
            select(func.count()).select_from(Milestone).where(Milestone.case_id == case_id)
        )
        or 0
    )


def get_task(session: Session, task_id: str) -> MilestoneTask | None:
    """One task."""
    return session.get(MilestoneTask, task_id)


def get_task_for_milestone(
    session: Session, milestone_id: str, task_id: str
) -> MilestoneTask | None:
    """One task, scoped to its milestone."""
    return session.scalars(
        select(MilestoneTask).where(
            MilestoneTask.id == task_id, MilestoneTask.milestone_id == milestone_id
        )
    ).first()


def list_tasks(session: Session, milestone_id: str) -> list[MilestoneTask]:
    """The tasks of a milestone, in order."""
    return list(
        session.scalars(
            select(MilestoneTask)
            .where(MilestoneTask.milestone_id == milestone_id)
            .order_by(MilestoneTask.order_index.asc(), MilestoneTask.id.asc())
        )
    )


def add_task(session: Session, task: MilestoneTask) -> MilestoneTask:
    """Store a new task."""
    session.add(task)
    return task


def delete_task(session: Session, task: MilestoneTask) -> None:
    """Remove a task."""
    session.delete(task)


def status_counts(session: Session, case_id: str) -> dict[str, int]:
    """How many milestones a case has per status."""
    from sqlalchemy import func

    rows = session.execute(
        select(Milestone.status, func.count())
        .where(Milestone.case_id == case_id)
        .group_by(Milestone.status)
    )
    counts = {status.value: 0 for status in MilestoneStatus}
    for status, count in rows:
        counts[status] = int(count)
    return counts
