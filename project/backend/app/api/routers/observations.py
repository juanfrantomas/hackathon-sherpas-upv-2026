"""Financial observation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import authorize_case, settings_dependency
from app.db.session import DbSession
from app.domain.enums import ObservationSource
from app.schemas.observation import (
    FinancialProgressResponse,
    ObservationCreateRequest,
    ObservationListResponse,
    ObservationResponse,
)
from app.services import (
    milestone_service,
    observation_service,
    progress_service,
)

router = APIRouter(prefix="/api/cases/{case_id}", tags=["observations"])


@router.post(
    "/milestones/{milestone_id}/observations",
    response_model=ObservationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_observation(
    case_id: str,
    milestone_id: str,
    payload: ObservationCreateRequest,
    session: DbSession,
    settings=Depends(settings_dependency),
) -> ObservationResponse:
    """Record a value the client declares."""
    case_id = authorize_case(case_id, settings)
    milestone = milestone_service.get_milestone(session, case_id, milestone_id)
    observation = observation_service.record_client_observation(
        session, milestone, payload
    )
    progress_service.compute_and_store(session, milestone)
    session.commit()
    session.refresh(observation)
    return ObservationResponse.model_validate(observation)


@router.get(
    "/milestones/{milestone_id}/observations", response_model=ObservationListResponse
)
async def list_observations(
    case_id: str,
    milestone_id: str,
    session: DbSession,
    metric_key: str | None = None,
    source: str | None = None,
    settings=Depends(settings_dependency),
) -> ObservationListResponse:
    """The observations of a milestone, with the disagreement between sources."""
    case_id = authorize_case(case_id, settings)
    milestone = milestone_service.get_milestone(session, case_id, milestone_id)
    observations = observation_service.list_observations(
        session, milestone, metric_key=metric_key, source=source
    )
    latest: dict[str, ObservationResponse] = {}
    for observation in observations:
        current = latest.get(observation.source)
        if current is None or observation.observed_at >= current.observed_at:
            latest[observation.source] = ObservationResponse.model_validate(observation)
    conflict = progress_service.conflict_detail(
        latest.get(ObservationSource.MCP.value),
        latest.get(ObservationSource.CLIENT.value),
    )
    return ObservationListResponse(
        observations=[
            ObservationResponse.model_validate(observation) for observation in observations
        ],
        conflict=conflict,
    )


@router.get(
    "/milestones/{milestone_id}/financial-progress",
    response_model=FinancialProgressResponse,
)
async def get_financial_progress(
    case_id: str,
    milestone_id: str,
    session: DbSession,
    settings=Depends(settings_dependency),
) -> FinancialProgressResponse:
    """The financial progress of a milestone and where the figures come from."""
    case_id = authorize_case(case_id, settings)
    milestone = milestone_service.get_milestone(session, case_id, milestone_id)
    result = progress_service.compute_and_store(session, milestone)
    session.commit()

    observations = progress_service.source_observations(session, milestone)
    latest: dict[str, ObservationResponse] = {}
    for observation in observations:
        current = latest.get(observation.source)
        if current is None or observation.observed_at >= current.observed_at:
            latest[observation.source] = ObservationResponse.model_validate(observation)
    conflict = progress_service.conflict_detail(
        latest.get(ObservationSource.MCP.value),
        latest.get(ObservationSource.CLIENT.value),
    )

    used_source = None
    if not conflict and latest:
        used_source = max(latest.values(), key=lambda item: item.observed_at).source

    return FinancialProgressResponse(
        milestone_id=milestone.id,
        progress=float(result.progress) if result.progress is not None else None,
        state=result.state.value,
        direction=milestone.financial_direction,
        start_value=milestone.financial_start_value,
        target_value=milestone.financial_target_value,
        used_source=used_source,
        sources=list(latest.values()),
        conflict=conflict,
        metric_key=milestone.financial_metric_key,
        unit=milestone.financial_unit,
        currency=milestone.financial_currency,
    )
