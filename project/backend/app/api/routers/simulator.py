"""The decision laboratory endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import (
    CaseContextDep,
    SettingsDep,
    ai_service_dependency,
    authorize_case,
)
from app.db.session import DbSession
from app.schemas.simulator import SimulatorRequest, SimulatorResponse
from app.services.simulator_service import SimulatorService

router = APIRouter(prefix="/api/cases/{case_id}", tags=["simulator"])


def _service(ai_service, context, settings) -> SimulatorService:
    return SimulatorService(
        ai_service, context, model=settings.ai_copy_model
    )


@router.get("/simulator", response_model=SimulatorResponse)
async def get_simulator(
    case_id: str,
    session: DbSession,
    context: CaseContextDep,
    settings: SettingsDep,
    ai_service=Depends(ai_service_dependency),
) -> SimulatorResponse:
    """The laboratory with the decisions the household switched on."""
    case_id = authorize_case(case_id, settings)
    service = _service(ai_service, context, settings)
    return await service.simulate(case_id, [])


@router.post("/simulator", response_model=SimulatorResponse)
async def simulate_decisions(
    case_id: str,
    payload: SimulatorRequest,
    session: DbSession,
    context: CaseContextDep,
    settings: SettingsDep,
    ai_service=Depends(ai_service_dependency),
) -> SimulatorResponse:
    """What the plan says about the decisions the household switched on."""
    case_id = authorize_case(case_id, settings)
    service = _service(ai_service, context, settings)
    return await service.simulate(case_id, payload.active_ids)
