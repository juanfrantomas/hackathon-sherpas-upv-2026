"""Progress rules.

Pure functions: no SQLAlchemy, no HTTP, no AI.  Everything here is unit
testable with plain Python values.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Protocol

from app.domain.enums import FinancialDirection, FinancialProgressState

#: Two values closer than this are considered the same figure.
TOLERANCE_ABS = Decimal("0.01")
#: Relative tolerance used for large figures (1 %).
TOLERANCE_REL = Decimal("0.01")


class HasTaskState(Protocol):
    """Structural type for anything that behaves like a task."""

    is_required: bool
    status: str


class HasObservation(Protocol):
    """Structural type for anything that behaves like an observation."""

    value: Decimal
    source: str
    observed_at: object
    is_conflicted: bool


@dataclass(frozen=True)
class FinancialProgress:
    """The outcome of a financial progress calculation."""

    progress: Decimal | None
    state: FinancialProgressState
    used_source: str | None = None
    regressed: bool = False

    @property
    def is_conflicting(self) -> bool:
        return self.state is FinancialProgressState.CONFLICTING


def _to_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def compute_task_progress(tasks: Sequence[HasTaskState]) -> int | None:
    """Completed required tasks / total required tasks * 100.

    Returns ``None`` when the milestone has no required tasks: the progress is
    *not applicable*, which is different from 0 %.
    """
    required = [task for task in tasks if task.is_required]
    if not required:
        return None
    completed = [task for task in required if task.status == "completed"]
    ratio = Decimal(len(completed)) / Decimal(len(required)) * Decimal(100)
    return int(ratio.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def average_task_progress(values: list[int | None]) -> int | None:
    """Average of the applicable task progresses (``None`` when there are none)."""
    applicable = [value for value in values if value is not None]
    if not applicable:
        return None
    total = sum(Decimal(value) for value in applicable)
    average = total / Decimal(len(applicable))
    return int(average.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def detect_conflict(
    mcp_value: Decimal | None,
    client_value: Decimal | None,
    *,
    tolerance_abs: Decimal = TOLERANCE_ABS,
    tolerance_rel: Decimal = TOLERANCE_REL,
) -> bool:
    """Whether two sources disagree materially.

    A conflict is only meaningful when both sources provided a value.
    """
    if mcp_value is None or client_value is None:
        return False
    difference = abs(mcp_value - client_value)
    if difference <= tolerance_abs:
        return False
    reference = max(abs(mcp_value), abs(client_value))
    if reference == 0:
        return False
    return difference > tolerance_rel * reference


def _clamp_percent(value: Decimal) -> Decimal:
    if value < 0:
        return Decimal("0")
    if value > 100:
        return Decimal("100")
    return value


def compute_financial_progress(
    *,
    direction: FinancialDirection | str | None,
    start_value: Decimal | None,
    target_value: Decimal | None,
    current_value: Decimal | None,
    conflicting: bool = False,
) -> FinancialProgress:
    """Compute the financial progress of a milestone.

    ``None`` is returned whenever a percentage would be an invention: no
    metric, no usable value, a target equal to the starting point, or an
    unresolved conflict between sources.
    """
    if conflicting:
        return FinancialProgress(progress=None, state=FinancialProgressState.CONFLICTING)

    start = _to_decimal(start_value)
    target = _to_decimal(target_value)
    current = _to_decimal(current_value)

    if direction is None or start is None or target is None or current is None:
        return FinancialProgress(
            progress=None, state=FinancialProgressState.NOT_QUANTIFIABLE
        )

    direction = FinancialDirection(direction)
    span = target - start
    if span == 0:
        return FinancialProgress(
            progress=None, state=FinancialProgressState.NOT_QUANTIFIABLE
        )

    if direction is FinancialDirection.INCREASE:
        raw = (current - start) / span * Decimal(100)
        regressed = current < start
    else:
        raw = (start - current) / (start - target) * Decimal(100)
        regressed = current > start

    if regressed:
        return FinancialProgress(
            progress=Decimal("0"),
            state=FinancialProgressState.REGRESSED,
            regressed=True,
        )

    clamped = _clamp_percent(raw)
    state = (
        FinancialProgressState.ACHIEVED
        if clamped >= 100
        else FinancialProgressState.ON_TRACK
    )
    return FinancialProgress(progress=clamped.quantize(Decimal("0.01")), state=state)


def select_current_observations(
    observations: list[HasObservation],
) -> dict[str, HasObservation]:
    """Latest observation per source for a given metric."""
    latest: dict[str, HasObservation] = {}
    for observation in observations:
        source = observation.source
        current = latest.get(source)
        if current is None or observation.observed_at >= current.observed_at:  # type: ignore[operator]
            latest[source] = observation
    return latest
