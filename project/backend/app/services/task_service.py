"""Task use cases: editing tasks and keeping the milestone progress in sync."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.domain.completion import should_auto_complete
from app.domain.enums import MilestoneStatus, TaskOrigin, TaskStatus
from app.domain.reconciliation import match_key
from app.errors import TaskNotFoundError
from app.models.milestone import Milestone
from app.models.task import MilestoneTask
from app.repositories import milestone_repository
from app.schemas.milestone import TaskCreateRequest, TaskUpdateRequest


def _new_task_id() -> str:
    return f"task_{uuid.uuid4().hex[:16]}"


def list_tasks(session: Session, milestone_id: str) -> list[MilestoneTask]:
    """The tasks of a milestone."""
    return milestone_repository.list_tasks(session, milestone_id)


def create_task(
    session: Session,
    milestone: Milestone,
    payload: TaskCreateRequest,
) -> MilestoneTask:
    """Add a task the client created."""
    order = payload.order
    if order is None:
        existing = milestone_repository.list_tasks(session, milestone.id)
        order = max((task.order_index for task in existing), default=-1) + 1
    task = MilestoneTask(
        id=_new_task_id(),
        milestone_id=milestone.id,
        title=payload.title,
        description=payload.description,
        order_index=order,
        is_required=payload.is_required,
        status=TaskStatus.PENDING.value,
        match_key=match_key(payload.title),
        origin=TaskOrigin.CLIENT.value,
    )
    milestone_repository.add_task(session, task)
    session.flush()
    recalculate_progress(session, milestone)
    return task


def update_task(
    session: Session,
    milestone: Milestone,
    task_id: str,
    payload: TaskUpdateRequest,
) -> MilestoneTask:
    """Complete, uncomplete or edit a task."""
    task = milestone_repository.get_task_for_milestone(session, milestone.id, task_id)
    if task is None:
        raise TaskNotFoundError(f"Task {task_id} does not exist for this milestone")

    if payload.status is not None:
        task.status = payload.status
        task.completed_at = (
            datetime.now(UTC)
            if payload.status == TaskStatus.COMPLETED.value
            else None
        )
    if payload.title is not None:
        task.title = payload.title
        task.match_key = match_key(payload.title)
    if payload.description is not None:
        task.description = payload.description
    if payload.is_required is not None:
        task.is_required = payload.is_required

    session.flush()
    recalculate_progress(session, milestone)
    return task


def delete_task(session: Session, milestone: Milestone, task_id: str) -> None:
    """Remove a task the client created."""
    task = milestone_repository.get_task_for_milestone(session, milestone.id, task_id)
    if task is None:
        raise TaskNotFoundError(f"Task {task_id} does not exist for this milestone")
    if task.origin == TaskOrigin.CLIENT.value:
        # Client tasks are removed through the API as well; this keeps the
        # rule that the synchronisation never deletes them.
        pass
    milestone_repository.delete_task(session, task)
    session.flush()
    recalculate_progress(session, milestone)


def recalculate_progress(session: Session, milestone: Milestone) -> int | None:
    """Recompute the operational progress and close educational milestones."""
    from app.domain.progress import compute_task_progress

    tasks = list(milestone.tasks)
    progress = compute_task_progress(tasks)
    milestone.task_progress = progress
    session.flush()

    if should_auto_complete(
        milestone_type=milestone.type,
        status=milestone.status,
        tasks=tasks,
    ):
        milestone.status = MilestoneStatus.COMPLETED.value
        milestone.completed_at = datetime.now(UTC)
        session.flush()
    return progress
