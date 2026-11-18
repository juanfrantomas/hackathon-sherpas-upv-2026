"""Completion rules."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.completion import (
    all_required_tasks_completed,
    has_required_tasks,
    should_auto_complete,
)


@dataclass
class FakeTask:
    is_required: bool
    status: str


def test_educational_milestone_closes_when_the_required_tasks_are_done():
    assert should_auto_complete(
        milestone_type="educational",
        status="in_progress",
        tasks=[FakeTask(True, "completed"), FakeTask(True, "completed")],
    )


def test_educational_milestone_stays_open_with_a_pending_task():
    assert not should_auto_complete(
        milestone_type="educational",
        status="in_progress",
        tasks=[FakeTask(True, "completed"), FakeTask(True, "pending")],
    )


def test_educational_milestone_without_required_tasks_needs_a_confirmation():
    assert not should_auto_complete(
        milestone_type="educational",
        status="in_progress",
        tasks=[FakeTask(False, "completed")],
    )


def test_financial_milestone_never_closes_on_its_own():
    assert not should_auto_complete(
        milestone_type="financial",
        status="in_progress",
        tasks=[FakeTask(True, "completed")],
    )


def test_a_closed_milestone_is_not_closed_again():
    assert not should_auto_complete(
        milestone_type="educational",
        status="completed",
        tasks=[FakeTask(True, "completed")],
    )


def test_helpers():
    tasks = [FakeTask(False, "pending"), FakeTask(True, "pending")]
    assert has_required_tasks(tasks) is True
    assert all_required_tasks_completed(tasks) is False
    assert all_required_tasks_completed([]) is False
