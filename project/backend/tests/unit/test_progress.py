"""Progress rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pytest

from app.domain.enums import FinancialDirection, FinancialProgressState
from app.domain.progress import (
    average_task_progress,
    compute_financial_progress,
    compute_task_progress,
    detect_conflict,
)


@dataclass
class FakeTask:
    is_required: bool
    status: str


def test_task_progress_counts_only_required_tasks():
    tasks = [
        FakeTask(True, "completed"),
        FakeTask(True, "pending"),
        FakeTask(False, "completed"),
    ]
    assert compute_task_progress(tasks) == 50


def test_task_progress_is_none_without_required_tasks():
    tasks = [FakeTask(False, "completed"), FakeTask(False, "pending")]
    assert compute_task_progress(tasks) is None


def test_task_progress_is_none_without_tasks():
    assert compute_task_progress([]) is None


def test_task_progress_is_one_hundred_when_all_are_done():
    tasks = [FakeTask(True, "completed"), FakeTask(True, "completed")]
    assert compute_task_progress(tasks) == 100


def test_average_task_progress_ignores_none():
    assert average_task_progress([50, None, 100]) == 75
    assert average_task_progress([None, None]) is None


def test_increasing_progress():
    result = compute_financial_progress(
        direction=FinancialDirection.INCREASE,
        start_value=Decimal("5000"),
        target_value=Decimal("20000"),
        current_value=Decimal("12500"),
    )
    assert result.progress == Decimal("50.00")
    assert result.state is FinancialProgressState.ON_TRACK


def test_decreasing_progress():
    result = compute_financial_progress(
        direction=FinancialDirection.DECREASE,
        start_value=Decimal("18000"),
        target_value=Decimal("0"),
        current_value=Decimal("9000"),
    )
    assert result.progress == Decimal("50.00")
    assert result.state is FinancialProgressState.ON_TRACK


def test_progress_is_clamped_at_one_hundred():
    result = compute_financial_progress(
        direction=FinancialDirection.INCREASE,
        start_value=Decimal("0"),
        target_value=Decimal("100"),
        current_value=Decimal("250"),
    )
    assert result.progress == Decimal("100")


def test_regression_is_zero_and_flagged():
    result = compute_financial_progress(
        direction=FinancialDirection.INCREASE,
        start_value=Decimal("5000"),
        target_value=Decimal("20000"),
        current_value=Decimal("4000"),
    )
    assert result.progress == Decimal("0")
    assert result.state is FinancialProgressState.REGRESSED
    assert result.regressed is True


def test_regression_for_a_decreasing_goal():
    result = compute_financial_progress(
        direction=FinancialDirection.DECREASE,
        start_value=Decimal("18000"),
        target_value=Decimal("0"),
        current_value=Decimal("20000"),
    )
    assert result.progress == Decimal("0")
    assert result.state is FinancialProgressState.REGRESSED


def test_equal_start_and_target_is_not_quantifiable():
    result = compute_financial_progress(
        direction=FinancialDirection.INCREASE,
        start_value=Decimal("100"),
        target_value=Decimal("100"),
        current_value=Decimal("120"),
    )
    assert result.progress is None
    assert result.state is FinancialProgressState.NOT_QUANTIFIABLE


def test_missing_metric_is_not_quantifiable():
    result = compute_financial_progress(
        direction=None,
        start_value=None,
        target_value=None,
        current_value=None,
    )
    assert result.progress is None
    assert result.state is FinancialProgressState.NOT_QUANTIFIABLE


def test_conflict_wins_over_everything():
    result = compute_financial_progress(
        direction=FinancialDirection.INCREASE,
        start_value=Decimal("0"),
        target_value=Decimal("100"),
        current_value=Decimal("50"),
        conflicting=True,
    )
    assert result.progress is None
    assert result.state is FinancialProgressState.CONFLICTING


@pytest.mark.parametrize(
    ("mcp", "client", "expected"),
    [
        (Decimal("18000"), Decimal("9000"), True),
        (Decimal("18000"), Decimal("18000"), False),
        (Decimal("18000"), Decimal("17900"), False),
        (Decimal("100"), Decimal("100.5"), False),
        (None, Decimal("9000"), False),
        (Decimal("18000"), None, False),
    ],
)
def test_conflict_detection(mcp, client, expected):
    assert detect_conflict(mcp, client) is expected
