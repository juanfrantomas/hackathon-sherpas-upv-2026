"""Persistence for financial cases."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.case import FinancialCase


def get_case(session: Session, case_id: str) -> FinancialCase | None:
    """The stored case, if any."""
    return session.get(FinancialCase, case_id)


def get_or_create_case(
    session: Session,
    case_id: str,
    *,
    household_name: str | None = None,
    data_source: str = "mcp",
    plan_language: str | None = None,
) -> FinancialCase:
    """Fetch the case or create it on the fly."""
    case = session.get(FinancialCase, case_id)
    now = datetime.now(UTC)
    if case is None:
        case = FinancialCase(
            id=case_id,
            household_name=household_name,
            data_source=data_source,
            plan_language=plan_language,
            first_seen_at=now,
            last_seen_at=now,
        )
        session.add(case)
        return case

    if household_name and case.household_name != household_name:
        case.household_name = household_name
    if plan_language and case.plan_language != plan_language:
        case.plan_language = plan_language
    if case.data_source != data_source:
        case.data_source = data_source
    case.last_seen_at = now
    return case


def list_cases(session: Session) -> list[FinancialCase]:
    """Every case we know about."""
    return list(session.scalars(select(FinancialCase).order_by(FinancialCase.id)))
