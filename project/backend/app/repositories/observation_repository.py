"""Persistence for financial observations."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.observation import FinancialObservation


def list_observations(
    session: Session,
    milestone_id: str,
    *,
    metric_key: str | None = None,
    source: str | None = None,
) -> list[FinancialObservation]:
    """The observations of a milestone."""
    query = select(FinancialObservation).where(
        FinancialObservation.milestone_id == milestone_id
    )
    if metric_key:
        query = query.where(FinancialObservation.metric_key == metric_key)
    if source:
        query = query.where(FinancialObservation.source == source)
    query = query.order_by(
        FinancialObservation.metric_key.asc(),
        FinancialObservation.source.asc(),
        FinancialObservation.observed_at.asc(),
    )
    return list(session.scalars(query))


def latest_by_source(
    session: Session, milestone_id: str, metric_key: str
) -> dict[str, FinancialObservation]:
    """The most recent observation per source for a metric."""
    observations = list_observations(session, milestone_id, metric_key=metric_key)
    latest: dict[str, FinancialObservation] = {}
    for observation in observations:
        current = latest.get(observation.source)
        if current is None or observation.observed_at >= current.observed_at:
            latest[observation.source] = observation
    return latest


def add_observation(
    session: Session, observation: FinancialObservation
) -> FinancialObservation:
    """Store a new observation."""
    session.add(observation)
    return observation


def observation_exists(
    session: Session,
    milestone_id: str,
    metric_key: str,
    source: str,
    observed_at: date,
) -> bool:
    """Whether an identical observation already exists."""
    existing = session.scalars(
        select(FinancialObservation)
        .where(
            FinancialObservation.milestone_id == milestone_id,
            FinancialObservation.metric_key == metric_key,
            FinancialObservation.source == source,
            FinancialObservation.observed_at == observed_at,
        )
        .limit(1)
    ).first()
    return existing is not None
