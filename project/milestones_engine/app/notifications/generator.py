"""Deterministic notice generation.

The generator lives in its own module so it can be called from the request
path and from the background loop without importing the services.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.services import notification_service


def evaluate_case(session: Session, case_id: str, *, today: date | None = None) -> int:
    """Create the notices that are due for a case."""
    return notification_service.evaluate(session, case_id, today=today)


def evaluate_all(session: Session, *, today: date | None = None) -> int:
    """Create the notices that are due for every known case."""
    from sqlalchemy import select

    from app.models.case import FinancialCase

    today = today or datetime.now(UTC).date()
    created = 0
    for case_id in session.scalars(select(FinancialCase.id)):
        created += evaluate_case(session, case_id, today=today)
    return created
