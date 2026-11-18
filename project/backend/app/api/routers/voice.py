"""The mentor endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket

from app.api.deps import (
    CaseContextDep,
    MentorServiceDep,
    SettingsDep,
    authorize_case,
    settings_dependency,
)
from app.domain.cases import get_short_id
from app.domain.voice_profiles import available_styles
from app.errors import AppError
from app.schemas.voice import MentorAskRequest, MentorAskResponse

router = APIRouter(prefix="/api", tags=["mentor"])


@router.post("/voice/ask", response_model=MentorAskResponse)
async def ask_the_mentor(
    payload: MentorAskRequest,
    mentor_service: MentorServiceDep,
    settings: SettingsDep,
) -> MentorAskResponse:
    """Ask the mentor a question about the plan of a household."""
    case_id = authorize_case(payload.case_id, settings)

    answer = await mentor_service.ask(
        case_id=case_id,
        question=payload.question,
        style=payload.style,
        partner=payload.partner,
        topic=payload.topic,
    )

    return MentorAskResponse(
        status="success",
        case_id=case_id,
        short_id=get_short_id(case_id),
        mcp_used=answer.mcp_used,
        voice=answer.voice_profile.get("voice_name", ""),
        style=answer.voice_profile.get("style_label", ""),
        style_key=answer.voice_profile.get("style_key", ""),
        partner_mode=payload.partner,
        consulted=answer.consulted,
        answer=answer.text,
        audio_url=answer.audio_url,
    )


@router.get("/voice/styles")
async def voice_styles(
    settings=Depends(settings_dependency),
) -> dict:
    """The registers the household can ask for."""
    return {"styles": available_styles()}


@router.websocket("/voice/ws/{case_id}")
async def voice_realtime(
    websocket: WebSocket,
    case_id: str,
    context: CaseContextDep,
    settings: SettingsDep,
) -> None:
    """The live voice channel of the mentor.

    The browser sends the audio of the household and receives the answer of
    the model.  The query carries the model, the register, the member of the
    couple who is speaking and the milestone that was opened.
    """
    from app.realtime.handler import handle_realtime_websocket

    try:
        slug = authorize_case(case_id, settings)
    except AppError as exc:
        await websocket.close(code=1008, reason=exc.code)
        return

    model = websocket.query_params.get("model") or settings.realtime_default_model
    if model not in settings.realtime_model_list:
        model = settings.realtime_default_model

    style = websocket.query_params.get("style")
    partner = websocket.query_params.get("partner", "auto")
    topic = websocket.query_params.get("topic")
    greet = websocket.query_params.get("greet", "0") in ("1", "true")

    await handle_realtime_websocket(
        websocket,
        slug,
        context=context,
        proxy_base_url=settings.realtime_base_url,
        token=settings.ai_api_key,
        model=model,
        style_override=style,
        partner_mode=partner,
        topic=topic,
        auto_greet=greet,
    )
