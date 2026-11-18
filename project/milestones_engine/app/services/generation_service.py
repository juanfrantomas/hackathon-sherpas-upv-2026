"""Generation: turning AI proposals into stored milestones.

The whole write happens in one transaction.  The AI call happens *before* the
transaction is opened, so no network call is ever made while the SQLite
write lock is held.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.enums import (
    FinancialDirection,
    MilestoneStatus,
    MilestoneType,
    ObservationSource,
    Priority,
    TaskOrigin,
    TaskStatus,
)
from app.domain.reconciliation import (
    MilestoneProposalSnapshot,
    MilestoneSnapshot,
    TaskProposalSnapshot,
    TaskSnapshot,
    match_key,
    reconcile_milestones,
    reconcile_tasks,
)
from app.integration.ai.ai_service import AIService, GenerationOutcome
from app.integration.mcp.digest import PlanDigest
from app.logging_config import get_logger
from app.models.generation import AIGeneration
from app.models.milestone import Milestone
from app.models.observation import FinancialObservation
from app.models.task import MilestoneTask
from app.repositories import milestone_repository, observation_repository
from app.schemas.generation import MilestoneProposal
from app.services import checkin_service, task_service

logger = get_logger(__name__)

#: The first review of a milestone, by priority.
CHECKIN_OFFSETS: dict[str, int] = {"high": 7, "medium": 14, "low": 30}


@dataclass
class GenerationSummary:
    """What one generation run changed."""

    created: int = 0
    updated: int = 0
    kept: int = 0
    generation_id: str | None = None
    model: str | None = None
    cost_usd: Decimal | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    repairs: int = 0


def stable_key_for(proposal: MilestoneProposal) -> tuple[str, str, str]:
    """The stable key of a proposal, plus the anchor it is built on.

    The key never depends on the order of the list nor on the wording of the
    title: it is the category plus the anchor inside the plan.
    """
    kind, _, value = proposal.anchor_key.partition(":")
    kind = kind.strip().lower() or "narrative"
    value = value.strip() or proposal.anchor_key.strip()
    stable_key = f"{proposal.category.slug}:{kind}:{value}"
    return stable_key, kind, value


def milestone_id_for(case_id: str, stable_key: str) -> str:
    """The identifier of a milestone: derived from the stable key."""
    digest = hashlib.sha1(f"{case_id}|{stable_key}".encode()).hexdigest()
    return f"ms_{digest[:16]}"


def _new_task_id() -> str:
    return f"task_{uuid.uuid4().hex[:16]}"


def _snapshot(milestone: Milestone) -> MilestoneSnapshot:
    return MilestoneSnapshot(
        id=milestone.id,
        stable_key=milestone.stable_key,
        title=milestone.title,
        action=milestone.action,
        category=milestone.category,
        section=milestone.section,
        status=milestone.status,
        anchor_kind=milestone.anchor_kind,
        anchor_value=milestone.anchor_value,
        tasks=[
            TaskSnapshot(
                id=task.id,
                title=task.title,
                status=task.status,
                is_required=task.is_required,
                origin=task.origin,
                order_index=task.order_index,
            )
            for task in milestone.tasks
        ],
    )


def _proposal_snapshot(
    proposal: MilestoneProposal, stable_key: str, kind: str, value: str
) -> MilestoneProposalSnapshot:
    return MilestoneProposalSnapshot(
        stable_key=stable_key,
        title=proposal.title,
        action=proposal.action,
        category=proposal.category.value,
        section=proposal.section.value,
        anchor_kind=kind,
        anchor_value=value,
        tasks=[
            TaskProposalSnapshot(
                title=task.title,
                is_required=task.is_required,
                order_index=task.order,
            )
            for task in proposal.tasks
        ],
    )


async def generate_milestones(
    session: Session,
    case_id: str,
    digest: PlanDigest,
    ai_service: AIService,
    *,
    plan_date: date | None = None,
) -> GenerationSummary:
    """Generate the milestones of a case and store them."""
    plan_date = plan_date or digest.plan_date or datetime.now(UTC).date()

    existing = milestone_repository.list_milestones(session, case_id)
    anchors = [
        f"{milestone.anchor_kind}:{milestone.anchor_value}"
        for milestone in existing
        if milestone.anchor_kind and milestone.anchor_value
    ]

    outcome: GenerationOutcome = await ai_service.generate_milestones(
        digest, existing_anchors=anchors
    )

    generation = AIGeneration(
        id=f"gen_{uuid.uuid4().hex[:16]}",
        case_id=case_id,
        model=outcome.model or ai_service.model,
        prompt_version=outcome.prompt_version,
        language=digest.language,
        input_tokens=outcome.input_tokens,
        output_tokens=outcome.output_tokens,
        cost_usd=outcome.cost_usd,
        raw_response=outcome.raw_response[:200_000],
        is_valid=True,
    )
    session.add(generation)
    session.flush()

    summary = GenerationSummary(
        generation_id=generation.id,
        model=generation.model,
        cost_usd=outcome.cost_usd,
        input_tokens=outcome.input_tokens,
        output_tokens=outcome.output_tokens,
        repairs=outcome.repairs,
    )

    proposals = outcome.result.milestones
    prepared = [
        (proposal, *stable_key_for(proposal)) for proposal in proposals
    ]
    snapshots = [
        _proposal_snapshot(proposal, stable_key, kind, value)
        for proposal, stable_key, kind, value in prepared
    ]
    existing_snapshots = [_snapshot(milestone) for milestone in existing]

    reconciliation = reconcile_milestones(existing_snapshots, snapshots)

    for proposal_index, existing_index in reconciliation.pairs.items():
        proposal = prepared[proposal_index][0]
        stable_key, kind, value = prepared[proposal_index][1:]
        milestone = existing[existing_index]
        _apply_to_existing(
            session,
            milestone,
            proposal,
            stable_key=stable_key,
            anchor_kind=kind,
            anchor_value=value,
        )
        summary.updated += 1

    for proposal_index in reconciliation.new_proposals:
        proposal = prepared[proposal_index][0]
        stable_key, kind, value = prepared[proposal_index][1:]
        milestone = _create_milestone(
            session,
            case_id,
            proposal,
            stable_key=stable_key,
            anchor_kind=kind,
            anchor_value=value,
            plan_date=plan_date,
            generation_id=generation.id,
        )
        _apply_tasks(session, milestone, proposal)
        _seed_observation(session, milestone, digest, plan_date)
        summary.created += 1

    for existing_index in reconciliation.unmatched_existing:
        milestone = existing[existing_index]
        milestone.is_stale = True
        summary.kept += 1

    session.flush()
    return summary


def _create_milestone(
    session: Session,
    case_id: str,
    proposal: MilestoneProposal,
    *,
    stable_key: str,
    anchor_kind: str,
    anchor_value: str,
    plan_date: date,
    generation_id: str | None,
) -> Milestone:
    """Store a brand new milestone."""
    milestone = Milestone(
        id=milestone_id_for(case_id, stable_key),
        case_id=case_id,
        stable_key=stable_key,
        title=proposal.title,
        why=proposal.why,
        action=proposal.action,
        section=proposal.section.value,
        category=proposal.category.value,
        type=proposal.type,
        priority=proposal.priority,
        priority_rank=Priority(proposal.priority).rank,
        status=MilestoneStatus.NOT_STARTED.value,
        source_refs=[ref.model_dump() for ref in proposal.source_refs],
        anchor_kind=anchor_kind,
        anchor_value=anchor_value,
        ai_generation_id=generation_id,
        due_date=_due_date(proposal, plan_date),
    )
    _apply_financial_target(milestone, proposal)
    milestone_repository.add_milestone(session, milestone)
    session.flush()
    checkin_service.schedule_first_checkin(
        session,
        milestone,
        scheduled=plan_date + timedelta(days=proposal.checkin_offset_days),
    )
    return milestone


def _apply_financial_target(
    milestone: Milestone, proposal: MilestoneProposal
) -> None:
    """Store the measurable goal of a milestone, when it has one."""
    target = proposal.financial_target
    if target is None:
        return
    milestone.financial_metric_key = target.metric_key
    milestone.financial_direction = target.direction
    milestone.financial_start_value = target.start_value
    milestone.financial_target_value = target.target_value
    milestone.financial_unit = target.unit
    milestone.financial_currency = target.currency


def _due_date(proposal: MilestoneProposal, plan_date: date) -> date | None:
    if proposal.due_offset_days is None:
        return None
    return plan_date + timedelta(days=proposal.due_offset_days)


def _apply_to_existing(
    session: Session,
    milestone: Milestone,
    proposal: MilestoneProposal,
    *,
    stable_key: str,
    anchor_kind: str,
    anchor_value: str,
) -> None:
    """Refresh the generated content of a milestone, keeping the client's work.

    The status, the completed tasks and the review schedule are never touched:
    the client owns them.
    """
    milestone.title = proposal.title
    milestone.why = proposal.why
    milestone.action = proposal.action
    milestone.section = proposal.section.value
    milestone.category = proposal.category.value
    milestone.type = proposal.type
    milestone.priority = proposal.priority
    milestone.priority_rank = Priority(proposal.priority).rank
    milestone.stable_key = stable_key
    milestone.anchor_kind = anchor_kind
    milestone.anchor_value = anchor_value
    milestone.source_refs = [ref.model_dump() for ref in proposal.source_refs]
    milestone.is_stale = False
    _apply_financial_target(milestone, proposal)
    _apply_tasks(session, milestone, proposal)
    session.flush()


def _apply_tasks(
    session: Session, milestone: Milestone, proposal: MilestoneProposal
) -> None:
    """Reconcile the tasks of a milestone with the new proposal."""
    existing = list(milestone.tasks)
    snapshots = [
        TaskSnapshot(
            id=task.id,
            title=task.title,
            status=task.status,
            is_required=task.is_required,
            origin=task.origin,
            order_index=task.order_index,
        )
        for task in existing
    ]
    proposals = [
        TaskProposalSnapshot(
            title=task.title,
            is_required=task.is_required,
            order_index=task.order,
        )
        for task in proposal.tasks
    ]
    result = reconcile_tasks(snapshots, proposals)
    by_id = {task.id: task for task in existing}

    for proposal_index, task_id in result.pairs.items():
        task = by_id[task_id]
        new_task = proposals[proposal_index]
        if task.origin != TaskOrigin.CLIENT.value:
            task.title = new_task.title
            task.match_key = match_key(new_task.title)
        task.is_required = new_task.is_required
        task.order_index = new_task.order_index
        task.ai_title = new_task.title

    for task_id in result.unmatched_tasks:
        task = by_id[task_id]
        if task.status == TaskStatus.COMPLETED.value:
            # Never lose progress: a completed task survives the rewrite.
            continue
        if task.origin == TaskOrigin.CLIENT.value:
            continue
        session.delete(task)

    for proposal_index in result.new_tasks:
        new_task = proposals[proposal_index]
        session.add(
            MilestoneTask(
                id=_new_task_id(),
                milestone_id=milestone.id,
                title=new_task.title,
                order_index=new_task.order_index,
                is_required=new_task.is_required,
                status=TaskStatus.PENDING.value,
                match_key=match_key(new_task.title),
                origin=TaskOrigin.AI.value,
            )
        )
    session.flush()
    session.refresh(milestone)
    task_service.recalculate_progress(session, milestone)


def _seed_observation(
    session: Session,
    milestone: Milestone,
    digest: PlanDigest,
    plan_date: date,
) -> None:
    """Store the figure the plan states for the milestone's metric."""
    target = milestone.financial_metric_key
    if not target:
        return
    metric = digest.metric_by_key(target)
    if metric is None:
        return
    if observation_repository.observation_exists(
        session, milestone.id, metric.metric_key, ObservationSource.MCP.value, plan_date
    ):
        return
    session.add(
        FinancialObservation(
            id=f"obs_{uuid.uuid4().hex[:16]}",
            milestone_id=milestone.id,
            metric_key=metric.metric_key,
            metric_type=metric.metric_type,
            value=metric.value,
            unit=metric.unit,
            currency=metric.currency,
            observed_at=plan_date,
            source=ObservationSource.MCP.value,
        )
    )
    session.flush()


__all__ = [
    "CHECKIN_OFFSETS",
    "GenerationSummary",
    "FinancialDirection",
    "MilestoneType",
    "generate_milestones",
    "milestone_id_for",
    "stable_key_for",
]
