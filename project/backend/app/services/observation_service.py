"""Financial observation use cases."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.domain.enums import ObservationSource
from app.errors import InvalidFinancialObservationError
from app.models.milestone import Milestone
from app.models.observation import FinancialObservation
from app.repositories import observation_repository
from app.schemas.observation import ObservationCreateRequest


def _new_observation_id() -> str:
    return f"obs_{uuid.uuid4().hex[:16]}"


def record_client_observation(
    session: Session,
    milestone: Milestone,
    payload: ObservationCreateRequest,
    *,
    today: date | None = None,
) -> FinancialObservation:
    """Store a value the client declares.

    Client observations never overwrite the ones coming from the MCP: both
    live side by side so the disagreement stays visible.
    """
    today = today or datetime.now(UTC).date()
    observed_at = payload.observed_at or today
    if observed_at > today:
        raise InvalidFinancialObservationError(
            "An observation cannot be dated in the future",
            details={"observed_at": observed_at.isoformat()},
        )
    if payload.value < 0:
        raise InvalidFinancialObservationError(
            "A financial observation cannot be negative",
            details={"value": str(payload.value)},
        )
    if not payload.unit.strip():
        raise InvalidFinancialObservationError("An observation needs a unit")

    observation = FinancialObservation(
        id=_new_observation_id(),
        milestone_id=milestone.id,
        metric_key=payload.metric_key,
        metric_type=payload.metric_type,
        value=payload.value,
        unit=payload.unit,
        currency=payload.currency,
        observed_at=observed_at,
        source=ObservationSource.CLIENT.value,
        note=payload.note,
    )
    observation_repository.add_observation(session, observation)
    session.flush()
    return observation


def list_observations(
    session: Session,
    milestone: Milestone,
    *,
    metric_key: str | None = None,
    source: str | None = None,
) -> list[FinancialObservation]:
    """The observations of a milestone."""
    return observation_repository.list_observations(
        session, milestone.id, metric_key=metric_key, source=source
    )
