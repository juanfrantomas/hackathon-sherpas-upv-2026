"""Reconciliation between generations.

The AI rewrites milestones and tasks on every generation.  This module decides
which new milestone corresponds to which stored one so that client progress
is never lost.

Identity never depends on the order of the list, on the position inside an
array or exclusively on the wording produced by the model: the primary key is
the *stable key* (an anchor derived from the plan), and the fallbacks are an
anchor match and a weighted text similarity.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

#: Weights of the weighted similarity used to pair milestones.
SIMILARITY_WEIGHTS = {
    "title": 0.45,
    "action": 0.20,
    "category": 0.20,
    "section": 0.15,
}

#: A milestone pair needs at least this combined similarity.
MILESTONE_MATCH_THRESHOLD = 0.62
#: ... and at least this similarity on the title alone.
TITLE_MATCH_THRESHOLD = 0.50
#: Tasks are matched with a lower bar: a reworded task is still the same task.
TASK_MATCH_THRESHOLD = 0.72

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "de", "del", "el",
    "for", "from", "has", "have", "he", "her", "his", "in", "is", "it", "its",
    "la", "las", "lo", "los", "of", "on", "or", "que", "she", "should", "so",
    "that", "the", "their", "them", "then", "there", "these", "they", "this",
    "to", "un", "una", "was", "were", "what", "when", "which", "who", "will",
    "with", "you", "your",
}


def strip_accents(text: str) -> str:
    """Replace accented characters with their base letter."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def normalize_text(text: str) -> str:
    """Lowercase, de-accent, drop punctuation and stop words, sort tokens."""
    lowered = strip_accents(text or "").lower()
    tokens = re.findall(r"[a-z0-9]+", lowered)
    meaningful = [token for token in tokens if token not in _STOPWORDS]
    if not meaningful:
        meaningful = tokens
    return " ".join(sorted(meaningful))


def match_key(title: str) -> str:
    """Stable key of a title, used to pair tasks across generations."""
    normalized = normalize_text(title)
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]


def title_similarity(left: str, right: str) -> float:
    """Similarity of two titles in the 0..1 range."""
    if not left or not right:
        return 0.0
    normalized_left = normalize_text(left)
    normalized_right = normalize_text(right)
    if not normalized_left or not normalized_right:
        return 0.0
    return SequenceMatcher(None, normalized_left, normalized_right).ratio()


@dataclass(frozen=True)
class MilestoneSnapshot:
    """The stored milestone, reduced to what matching needs."""

    id: str
    stable_key: str
    title: str
    action: str
    category: str
    section: str
    status: str
    anchor_kind: str | None = None
    anchor_value: str | None = None
    tasks: list[TaskSnapshot] = field(default_factory=list)


@dataclass(frozen=True)
class TaskSnapshot:
    """The stored task, reduced to what matching needs."""

    id: str
    title: str
    status: str
    is_required: bool
    origin: str
    order_index: int


@dataclass(frozen=True)
class MilestoneProposalSnapshot:
    """A milestone proposed by the AI, reduced to what matching needs."""

    stable_key: str
    title: str
    action: str
    category: str
    section: str
    anchor_kind: str | None = None
    anchor_value: str | None = None
    tasks: list[TaskProposalSnapshot] = field(default_factory=list)


@dataclass(frozen=True)
class TaskProposalSnapshot:
    """A task proposed by the AI."""

    title: str
    is_required: bool
    order_index: int


def milestone_similarity(
    existing: MilestoneSnapshot, proposal: MilestoneProposalSnapshot
) -> float:
    """Weighted similarity between a stored milestone and a proposal."""
    score = 0.0
    score += SIMILARITY_WEIGHTS["title"] * title_similarity(
        existing.title, proposal.title
    )
    score += SIMILARITY_WEIGHTS["action"] * title_similarity(
        existing.action, proposal.action
    )
    score += SIMILARITY_WEIGHTS["category"] * (
        1.0 if existing.category == proposal.category else 0.0
    )
    score += SIMILARITY_WEIGHTS["section"] * (
        1.0 if existing.section == proposal.section else 0.0
    )
    return score


def _exact_key_match(
    existing: list[MilestoneSnapshot], proposal: MilestoneProposalSnapshot
) -> int | None:
    for index, candidate in enumerate(existing):
        if candidate.stable_key and candidate.stable_key == proposal.stable_key:
            return index
    return None


def _anchor_match(
    existing: list[MilestoneSnapshot], proposal: MilestoneProposalSnapshot
) -> int | None:
    if not proposal.anchor_kind or not proposal.anchor_value:
        return None
    for index, candidate in enumerate(existing):
        if (
            candidate.anchor_kind == proposal.anchor_kind
            and candidate.anchor_value == proposal.anchor_value
        ):
            return index
    return None


@dataclass(frozen=True)
class ReconciliationResult:
    """How proposals map onto stored milestones."""

    #: proposal index -> existing index
    pairs: dict[int, int] = field(default_factory=dict)
    #: indices of proposals with no match (new milestones)
    new_proposals: list[int] = field(default_factory=list)
    #: indices of stored milestones with no match
    unmatched_existing: list[int] = field(default_factory=list)

    @property
    def matched_proposals(self) -> set[int]:
        return set(self.pairs.keys())


def reconcile_milestones(
    existing: list[MilestoneSnapshot],
    proposals: list[MilestoneProposalSnapshot],
) -> ReconciliationResult:
    """Pair proposals with stored milestones.

    Three passes, in decreasing confidence: exact stable key, shared anchor,
    then weighted text similarity.  The similarity pass assigns greedily, best
    score first, so the outcome is deterministic for a given input.
    """
    pairs: dict[int, int] = {}
    used_existing: set[int] = set()

    # Pass 1 - exact stable key.
    for proposal_index, proposal in enumerate(proposals):
        if proposal_index in pairs:
            continue
        match = _exact_key_match(
            [e for i, e in enumerate(existing) if i not in used_existing], proposal
        )
        if match is None:
            continue
        candidate_index = next(
            i
            for i, e in enumerate(existing)
            if i not in used_existing and e.stable_key == proposal.stable_key
        )
        pairs[proposal_index] = candidate_index
        used_existing.add(candidate_index)

    # Pass 2 - shared anchor.
    for proposal_index, proposal in enumerate(proposals):
        if proposal_index in pairs:
            continue
        available = [
            (i, e) for i, e in enumerate(existing) if i not in used_existing
        ]
        for candidate_index, candidate in available:
            if (
                proposal.anchor_kind
                and proposal.anchor_value
                and candidate.anchor_kind == proposal.anchor_kind
                and candidate.anchor_value == proposal.anchor_value
            ):
                pairs[proposal_index] = candidate_index
                used_existing.add(candidate_index)
                break

    # Pass 3 - weighted similarity, greedy and deterministic.
    scored: list[tuple[float, int, int]] = []
    for proposal_index, proposal in enumerate(proposals):
        if proposal_index in pairs:
            continue
        for candidate_index, candidate in enumerate(existing):
            if candidate_index in used_existing:
                continue
            score = milestone_similarity(candidate, proposal)
            title_score = title_similarity(candidate.title, proposal.title)
            if score >= MILESTONE_MATCH_THRESHOLD and title_score >= TITLE_MATCH_THRESHOLD:
                scored.append((score, proposal_index, candidate_index))

    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    for _score, proposal_index, candidate_index in scored:
        if proposal_index in pairs or candidate_index in used_existing:
            continue
        pairs[proposal_index] = candidate_index
        used_existing.add(candidate_index)

    new_proposals = [i for i in range(len(proposals)) if i not in pairs]
    unmatched_existing = [i for i in range(len(existing)) if i not in used_existing]
    return ReconciliationResult(
        pairs=pairs, new_proposals=new_proposals, unmatched_existing=unmatched_existing
    )


@dataclass(frozen=True)
class TaskReconciliationResult:
    """How proposed tasks map onto stored tasks."""

    #: proposal index -> existing task id
    pairs: dict[int, str] = field(default_factory=dict)
    #: stored task ids with no matching proposal (completed ones are kept)
    unmatched_tasks: list[str] = field(default_factory=list)
    #: proposal indices with no matching stored task
    new_tasks: list[int] = field(default_factory=list)


def reconcile_tasks(
    existing: list[TaskSnapshot], proposals: list[TaskProposalSnapshot]
) -> TaskReconciliationResult:
    """Pair proposed tasks with stored tasks.

    A stored task that was completed is always kept, even when the proposal
    no longer mentions it: losing a completed task would lose progress.
    """
    pairs: dict[int, str] = {}
    used: set[str] = set()

    # Pass 1 - exact match key.
    for proposal_index, proposal in enumerate(proposals):
        key = match_key(proposal.title)
        for task in existing:
            if task.id in used:
                continue
            if task.origin == "client":
                continue
            if match_key(task.title) == key:
                pairs[proposal_index] = task.id
                used.add(task.id)
                break

    # Pass 2 - similarity, for reworded tasks.
    scored: list[tuple[float, int, str]] = []
    for proposal_index, proposal in enumerate(proposals):
        if proposal_index in pairs:
            continue
        for task in existing:
            if task.id in used or task.origin == "client":
                continue
            score = title_similarity(task.title, proposal.title)
            if score >= TASK_MATCH_THRESHOLD:
                scored.append((score, proposal_index, task.id))

    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    for _score, proposal_index, task_id in scored:
        if proposal_index in pairs or task_id in used:
            continue
        pairs[proposal_index] = task_id
        used.add(task_id)

    unmatched_tasks = [task.id for task in existing if task.id not in used]
    new_tasks = [i for i in range(len(proposals)) if i not in pairs]
    return TaskReconciliationResult(
        pairs=pairs, unmatched_tasks=unmatched_tasks, new_tasks=new_tasks
    )
