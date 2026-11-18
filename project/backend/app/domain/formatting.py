"""Small formatting helpers shared by the API layer."""

from __future__ import annotations

from datetime import date

_MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def format_checkin_display(value: date | None) -> str | None:
    """The check-in date in the format the React client already renders.

    The prototype shows ``"Dec 14"``; keeping that exact shape avoids a
    breaking change in the frontend.
    """
    if value is None:
        return None
    return f"{_MONTHS[value.month - 1]} {value.day}"


def format_due_display(value: date | None) -> str | None:
    """A due date with the year, because a target date needs one."""
    if value is None:
        return None
    return f"{_MONTHS[value.month - 1]} {value.day}, {value.year}"
