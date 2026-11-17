"""Financial progress: how far a milestone got with a measurable goal."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.domain.enums import FinancialProgressState
from app.domain.progress import (
    FinancialProgress,
    compute_financial_progress,
    detect_conflict,
)
from app.models.milestone import Milestone
from app.models.observation import FinancialObservation
from app.repositories import observation_repository


def _pick_current(
    mcp: FinancialObservation | None, client: FinancialObservation | None
) -> FinancialObservation | None:
    """The value used for the calculation when the sources agree.

    The most recent observation wins; the client is only preferred when it is
    the newer one.
    """
    if mcp is None:
        return client
    if client is None:
        return mcp
    return client if client.observed_at >= mcp.observed_at else mcp


def compute_and_store(
    session: Session, milestone: Milestone
) -> FinancialProgress:
    """Recompute the financial progress of a milestone and store it."""
    metric_key = milestone.financial_metric_key
    if not metric_key or milestone.financial_target_value is None:
        milestone.financial_progress = None
        milestone.financial_progress_state = (
            FinancialProgressState.NOT_QUANTIFIABLE.value
        )
        session.flush()
        return FinancialProgress(
            progress=None, state=FinancialProgressState.NOT_QUANTIFIABLE
        )

    latest = observation_repository.latest_by_source(session, milestone.id, metric_key)
    mcp = latest.get("mcp")
    client = latest.get("client")

    mcp_value = mcp.value if mcp is not None else None
    client_value = client.value if client is not None else None
    conflict = detect_conflict(mcp_value, client_value)

    for observation in latest.values():
        observation.is_conflicted = conflict

    current = _pick_current(mcp, client)
    current_value = current.value if current is not None else None

    result = compute_financial_progress(
        direction=milestone.financial_direction,
        start_value=milestone.financial_start_value,
        target_value=milestone.financial_target_value,
        current_value=current_value,
        conflicting=conflict,
    )
    if conflict:
        result = FinancialProgress(
            progress=None,
            state=FinancialProgressState.CONFLICTING,
        )

    milestone.financial_progress = (
        result.progress if result.progress is not None else None
    )
    milestone.financial_progress_state = result.state.value
    session.flush()
    return result


def conflict_detail(mcp: Any, client: Any) -> dict | None:
    """A description of the disagreement between two sources."""
    if mcp is None or client is None:
        return None
    difference = abs(Decimal(str(mcp.value)) - Decimal(str(client.value)))
    return {
        "metric_key": mcp.metric_key,
        "mcp_value": str(mcp.value),
        "mcp_observed_at": mcp.observed_at.isoformat(),
        "client_value": str(client.value),
        "client_observed_at": client.observed_at.isoformat(),
        "difference": str(difference),
        "resolution": "Declare a new value or let the advisor update the plan",
    }


def source_observations(
    session: Session, milestone: Milestone
) -> list[FinancialObservation]:
    """The observations that feed the calculation."""
    if not milestone.financial_metric_key:
        return []
    return observation_repository.list_observations(
        session, milestone.id, metric_key=milestone.financial_metric_key
    )
