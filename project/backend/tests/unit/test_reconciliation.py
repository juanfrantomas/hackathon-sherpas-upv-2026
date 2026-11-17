"""Reconciliation between two generations."""

from __future__ import annotations

from app.domain.reconciliation import (
    MilestoneProposalSnapshot,
    MilestoneSnapshot,
    TaskProposalSnapshot,
    TaskSnapshot,
    match_key,
    normalize_text,
    reconcile_milestones,
    reconcile_tasks,
    title_similarity,
)


def snapshot(**kwargs) -> MilestoneSnapshot:
    defaults = {
        "id": "ms_1",
        "stable_key": "debt:concern:O2",
        "title": "Understand your credit card debt",
        "action": "Read the debt section",
        "category": "Debt",
        "section": "debt",
        "status": "not_started",
        "anchor_kind": "concern",
        "anchor_value": "O2",
    }
    defaults.update(kwargs)
    return MilestoneSnapshot(**defaults)


def proposal(**kwargs) -> MilestoneProposalSnapshot:
    defaults = {
        "stable_key": "debt:concern:O2",
        "title": "Understand your credit card debt",
        "action": "Read the debt section",
        "category": "Debt",
        "section": "debt",
        "anchor_kind": "concern",
        "anchor_value": "O2",
    }
    defaults.update(kwargs)
    return MilestoneProposalSnapshot(**defaults)


def test_normalisation_drops_stop_words_and_accents():
    assert normalize_text("Review the Debt Section!") == "debt review section"


def test_match_key_is_stable_for_the_same_title():
    assert match_key("Read the debt section") == match_key("read  the DEBT section")


def test_title_similarity_ignores_the_wording():
    assert title_similarity("Read the debt section", "read debt section") > 0.8


def test_exact_stable_key_matches():
    result = reconcile_milestones([snapshot()], [proposal()])
    assert result.pairs == {0: 0}
    assert result.new_proposals == []


def test_anchor_matches_even_when_the_category_changes():
    result = reconcile_milestones(
        [snapshot()],
        [proposal(stable_key="savings:concern:O2", category="Savings")],
    )
    assert result.pairs == {0: 0}


def test_a_different_milestone_is_a_new_one():
    result = reconcile_milestones(
        [snapshot()],
        [
            proposal(
                stable_key="savings:metric:account_cash_account",
                anchor_kind="metric",
                anchor_value="account_cash_account",
                title="Review your savings strategy",
                action="Open Savings and Expenses",
                category="Savings",
                section="savings",
            )
        ],
    )
    assert result.pairs == {}
    assert result.new_proposals == [0]
    assert result.unmatched_existing == [0]


def test_a_reworded_milestone_is_still_the_same_one():
    result = reconcile_milestones(
        [snapshot()],
        [
            proposal(
                stable_key="debt:concern:O2",
                title="Understand your credit card debt in detail",
                action="Read the debt section of the plan carefully",
            )
        ],
    )
    assert result.pairs == {0: 0}


def test_reconciliation_is_deterministic():
    existing = [snapshot(), snapshot(id="ms_2", stable_key="savings:metric:cash")]
    proposals = [proposal(), proposal(stable_key="savings:metric:cash", title="Savings")]
    first = reconcile_milestones(existing, proposals)
    second = reconcile_milestones(existing, proposals)
    assert first.pairs == second.pairs


def test_tasks_match_by_key():
    existing = [
        TaskSnapshot(
            id="t1",
            title="Read the debt section",
            status="completed",
            is_required=True,
            origin="ai",
            order_index=0,
        )
    ]
    proposals = [TaskProposalSnapshot(title="Read the debt section", is_required=True, order_index=0)]
    result = reconcile_tasks(existing, proposals)
    assert result.pairs == {0: "t1"}
    assert result.unmatched_tasks == []


def test_a_reworded_task_is_still_the_same_task():
    existing = [
        TaskSnapshot(
            id="t1",
            title="Read the debt section",
            status="completed",
            is_required=True,
            origin="ai",
            order_index=0,
        )
    ]
    proposals = [
        TaskProposalSnapshot(title="Read the debt section of the plan", is_required=True, order_index=0)
    ]
    result = reconcile_tasks(existing, proposals)
    assert result.pairs == {0: "t1"}


def test_a_completed_task_survives_even_without_a_match():
    existing = [
        TaskSnapshot(
            id="t1",
            title="Something entirely different",
            status="completed",
            is_required=True,
            origin="ai",
            order_index=0,
        )
    ]
    proposals = [
        TaskProposalSnapshot(title="Read the debt section of the plan", is_required=True, order_index=0)
    ]
    result = reconcile_tasks(existing, proposals)
    assert result.pairs == {}
    assert result.unmatched_tasks == ["t1"]


def test_client_tasks_are_never_matched_or_dropped():
    existing = [
        TaskSnapshot(
            id="t1",
            title="Call the bank",
            status="pending",
            is_required=False,
            origin="client",
            order_index=0,
        )
    ]
    proposals = [TaskProposalSnapshot(title="Call the bank", is_required=False, order_index=0)]
    result = reconcile_tasks(existing, proposals)
    assert result.pairs == {}
    assert result.unmatched_tasks == ["t1"]
