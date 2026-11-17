"""Synchronisation: keep the milestones in step with the financial plan."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import SyncConflictError
from app.integration.ai.ai_service import AIService
from app.integration.mcp.case_source import CaseSource
from app.logging_config import get_logger
from app.repositories import notification_repository
from app.services import case_service, generation_service, notification_service
from app.services.generation_service import GenerationSummary

logger = get_logger(__name__)


@dataclass
class SyncSummary:
    """The outcome of a synchronisation."""

    changed: bool
    reason: str
    created: int = 0
    updated: int = 0
    kept: int = 0
    plan_fingerprint: str | None = None
    model: str | None = None
    cost_usd: object | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


async def sync_case(
    session: Session,
    case_id: str,
    case_source: CaseSource,
    ai_service: AIService,
    settings: Settings,
    *,
    trigger: str = "manual",
    force: bool = False,
) -> SyncSummary:
    """Bring the milestones of a case in line with the current plan.

    Nothing is written when the plan did not change: the fingerprint of the
    digest is compared with the one stored in the last successful run.
    """
    case_service.ensure_case_row(session, case_id)
    state = notification_repository.get_or_create_sync_state(session, case_id)
    if not notification_repository.claim_sync(session, case_id):
        raise SyncConflictError(
            "A synchronisation is already running for this case",
            details={"case_id": case_id},
        )

    try:
        digest = await case_service.get_digest(case_source, case_id)
        fingerprint = digest.fingerprint

        if not force and state.plan_fingerprint == fingerprint and state.last_success_at:
            logger.info("The plan of %s did not change, skipping the sync", case_id)
            state.status = "success"
            state.trigger = trigger
            session.flush()
            return SyncSummary(
                changed=False,
                reason="plan_unchanged",
                plan_fingerprint=fingerprint,
            )

        if (
            not force
            and trigger != "manual"
            and state.last_success_at
            and settings.sync_min_interval_minutes > 0
        ):
            elapsed = datetime.now(UTC) - state.last_success_at
            if elapsed < timedelta(minutes=settings.sync_min_interval_minutes):
                state.status = "success"
                state.trigger = trigger
                session.flush()
                return SyncSummary(
                    changed=False,
                    reason="interval_not_elapsed",
                    plan_fingerprint=fingerprint,
                )

        case_service.ensure_case(
            session, case_id, digest, data_source=getattr(case_source, "data_source", "mcp")
        )

        summary: GenerationSummary = await generation_service.generate_milestones(
            session, case_id, digest, ai_service
        )

        state.status = "success"
        state.trigger = trigger
        state.plan_fingerprint = fingerprint
        state.last_success_at = datetime.now(UTC)
        state.last_error_code = None
        state.last_error_message = None
        state.milestones_created = summary.created
        state.milestones_updated = summary.updated
        state.milestones_kept = summary.kept
        state.ai_model = summary.model
        session.flush()

        notification_service.evaluate(session, case_id)
        session.flush()

        return SyncSummary(
            changed=True,
            reason="synchronised",
            created=summary.created,
            updated=summary.updated,
            kept=summary.kept,
            plan_fingerprint=fingerprint,
            model=summary.model,
            cost_usd=summary.cost_usd,
            input_tokens=summary.input_tokens,
            output_tokens=summary.output_tokens,
        )
    except Exception as exc:
        state.status = "error"
        state.trigger = trigger
        state.last_error_code = getattr(exc, "code", type(exc).__name__)
        state.last_error_message = str(exc)[:500]
        session.flush()
        raise
