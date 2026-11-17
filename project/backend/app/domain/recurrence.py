"""Deterministic monthly recurrence.

Check-ins are planned with a fixed monthly rule.  No AI call is involved:
the next review date is always ``scheduled + 1 month`` (or more, if the
review happened very late).
"""

from __future__ import annotations

import calendar
from datetime import date


def add_months(source: date, months: int) -> date:
    """Add ``months`` to a date, clamping to the end of the target month.

    ``31 January + 1 month`` is ``28 February`` (or 29 in a leap year) and
    ``31 March + 1 month`` is ``30 April``.
    """
    if months == 0:
        return source
    total_months = source.month - 1 + months
    year = source.year + total_months // 12
    month = total_months % 12 + 1
    day = min(source.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def next_review_date(scheduled: date, *, today: date | None = None) -> date:
    """The next monthly review after ``scheduled``.

    The date is anchored to the *scheduled* date so a late review does not
    make the schedule drift.  If the resulting date is already in the past the
    schedule is advanced month by month until it is not.
    """
    candidate = add_months(scheduled, 1)
    if today is None:
        return candidate
    guard = 0
    while candidate < today and guard < 600:
        candidate = add_months(candidate, 1)
        guard += 1
    return candidate


def is_checkin_pending(
    *,
    scheduled_date: date | None,
    status: str,
    today: date,
    review_completed: bool = False,
) -> bool:
    """Whether a milestone is waiting for its review.

    A milestone that is completed or cancelled never has a pending review.
    """
    if scheduled_date is None:
        return False
    if status in {"completed", "cancelled"}:
        return False
    if review_completed:
        return False
    return today > scheduled_date


def is_overdue(*, due_date: date | None, status: str, today: date) -> bool:
    """Whether a milestone passed its target date without being closed."""
    if due_date is None:
        return False
    if status in {"completed", "cancelled"}:
        return False
    return due_date < today
