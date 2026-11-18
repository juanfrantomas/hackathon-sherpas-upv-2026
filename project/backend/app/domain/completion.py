"""Completion rules for milestones."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.domain.enums import MilestoneStatus, MilestoneType


class HasTaskState(Protocol):
    is_required: bool
    status: str


def has_required_tasks(tasks: Sequence[HasTaskState]) -> bool:
    """Whether the milestone carries at least one required task."""
    return any(task.is_required for task in tasks)


def all_required_tasks_completed(tasks: Sequence[HasTaskState]) -> bool:
    """Whether every required task is done.

    A milestone without required tasks is *not* auto-completed: it needs an
    explicit confirmation from the client.
    """
    required = [task for task in tasks if task.is_required]
    if not required:
        return False
    return all(task.status == "completed" for task in required)


def should_auto_complete(
    *,
    milestone_type: MilestoneType | str,
    status: MilestoneStatus | str,
    tasks: Sequence[HasTaskState],
) -> bool:
    """Whether completing the tasks is enough to close the milestone.

    Educational milestones close themselves once their required tasks are
    done.  Financial milestones always need an explicit client confirmation:
    closing them is a statement about money, not about paperwork.
    """
    milestone_type = MilestoneType(milestone_type)
    status = MilestoneStatus(status)
    if milestone_type is not MilestoneType.EDUCATIONAL:
        return False
    if status in {MilestoneStatus.COMPLETED, MilestoneStatus.CANCELLED}:
        return False
    return all_required_tasks_completed(tasks)
