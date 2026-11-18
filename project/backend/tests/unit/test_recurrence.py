"""Monthly recurrence and the derived indicators."""

from __future__ import annotations

from datetime import date

import pytest

from app.domain.recurrence import (
    add_months,
    is_checkin_pending,
    is_overdue,
    next_review_date,
)


@pytest.mark.parametrize(
    ("source", "months", "expected"),
    [
        (date(2026, 1, 31), 1, date(2026, 2, 28)),
        (date(2028, 1, 31), 1, date(2028, 2, 29)),
        (date(2026, 3, 31), 1, date(2026, 4, 30)),
        (date(2026, 12, 31), 1, date(2027, 1, 31)),
        (date(2026, 1, 15), 3, date(2026, 4, 15)),
        (date(2026, 6, 30), 6, date(2026, 12, 30)),
        (date(2026, 5, 31), 0, date(2026, 5, 31)),
    ],
)
def test_add_months(source, months, expected):
    assert add_months(source, months) == expected


def test_next_review_is_one_month_after_the_scheduled_date():
    assert next_review_date(date(2026, 12, 14)) == date(2027, 1, 14)


def test_next_review_keeps_the_schedule_when_the_review_was_late():
    scheduled = date(2026, 12, 14)
    assert next_review_date(scheduled, today=date(2027, 3, 2)) == date(2027, 3, 14)


def test_next_review_never_lands_in_the_past():
    result = next_review_date(date(2026, 1, 14), today=date(2027, 6, 1))
    assert result >= date(2027, 6, 1)


def test_checkin_is_pending_after_the_scheduled_date():
    assert (
        is_checkin_pending(
            scheduled_date=date(2026, 12, 14),
            status="in_progress",
            today=date(2026, 12, 15),
        )
        is True
    )


def test_checkin_is_not_pending_on_the_scheduled_date():
    assert (
        is_checkin_pending(
            scheduled_date=date(2026, 12, 14),
            status="in_progress",
            today=date(2026, 12, 14),
        )
        is False
    )


def test_checkin_is_never_pending_for_a_closed_milestone():
    for status in ("completed", "cancelled"):
        assert (
            is_checkin_pending(
                scheduled_date=date(2026, 12, 14),
                status=status,
                today=date(2027, 1, 1),
            )
            is False
        )


def test_overdue_needs_a_due_date_in_the_past():
    assert (
        is_overdue(due_date=date(2026, 12, 14), status="in_progress", today=date(2026, 12, 15))
        is True
    )
    assert (
        is_overdue(due_date=date(2026, 12, 14), status="in_progress", today=date(2026, 12, 14))
        is False
    )
    assert is_overdue(due_date=None, status="in_progress", today=date(2027, 1, 1)) is False


def test_overdue_ignores_closed_milestones():
    assert (
        is_overdue(due_date=date(2026, 12, 14), status="completed", today=date(2027, 1, 1))
        is False
    )
