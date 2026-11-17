"""Persistence for the high fives of a household."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.family_high_five import FamilyHighFive


def list_high_fives(session: Session, case_id: str) -> list[FamilyHighFive]:
    """The wall of high fives of a household, newest first."""
    return list(
        session.scalars(
            select(FamilyHighFive)
            .where(FamilyHighFive.case_id == case_id)
            .order_by(FamilyHighFive.created_at.desc())
        )
    )


def add_high_five(
    session: Session,
    case_id: str,
    *,
    from_member: str,
    to_member: str,
    milestone_title: str,
    message: str,
) -> FamilyHighFive:
    """Store a new high five."""
    high_five = FamilyHighFive(
        id=f"hf_{uuid.uuid4().hex[:16]}",
        case_id=case_id,
        from_member=from_member,
        to_member=to_member,
        milestone_title=milestone_title,
        message=message,
        created_at=datetime.now(UTC),
    )
    session.add(high_five)
    session.flush()
    return high_five
