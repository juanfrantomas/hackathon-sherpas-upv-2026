"""
routes/api.py
-------------
Controlador de rutas HTTP REST de la API:
- GET /: Sirve el Centro Interactivo (Voz Realtime + Mapa de Viaje + Simulador What-If + Traductor de Jerga + Multijugador).
- GET /prototype: Sirve el prototipo móvil completo (MySherpas-prototype.html).
- GET /api/cases: Lista las 4 familias con sus IDs cortos/largos, scores, voces y si son pareja.
- GET /api/path/{client_id}: Devuelve el Mapa de Viaje (niveles + paradas de metas vitales + Modo Multijugador).
- POST /api/path/{client_id}/milestone: Marca un nivel como completado, lanza micro-victoria/confeti y sube el Score.
- POST /api/path/{client_id}/reset: Reinicia el progreso de la familia para la demo.
- GET /api/simulator/{client_id} y POST /api/simulator/{client_id}: Simulador interactivo '¿Qué pasaría si...?' (What-If).
- GET /api/mentor/insights/{client_id}: Mentor IA Proactivo + Traductor de Jerga con metáforas visuales.
- GET /api/couple/{client_id} y POST /api/couple/{client_id}/high-five: Modo Multijugador Familiar (Pareja + Vista Hijos).
- GET /api/story/{client_id}: Vídeo Introductorio ('Your Financial Story').
- POST /api/voice/ask: Endpoint HTTP tradicional con Tool Calling y caché de ElevenLabs.
"""

import os
import asyncio
from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from models import (
    PathSchema,
    MilestoneUpdateRequest,
    HighFiveRequest,
    CoupleOverview,
    SimulatorRequest,
    SimulatorResponse,
    MentorInsightsResponse,
    StorySchema,
)
from mcp_client import (
    normalize_case_id,
    get_short_id,
    get_compact_client_context,
    get_couple_dynamics,
    build_realtime_brief,
    SHORT_ID_MAP,
)
from services.voice_profiles import resolve_voice_profile
from services.ai_service import (
    ask_llm_with_tools,
    synthesize_elevenlabs_speech,
    build_gamified_path,
    update_milestone_state,
    reset_client_path,
    run_what_if_simulator,
    get_mentor_insights,
    add_high_five,
    build_financial_story,
)

router = APIRouter()


class VoiceQuery(BaseModel):
    client_id: str
    question: str
    style: str = "auto"
    partner: Optional[str] = "auto"
    topic: Optional[str] = None


@router.get("/")
async def serve_voice_tester():
    """Sirve la consola interactiva con Voz Realtime y los 5 pilares del producto."""
    test_html = os.path.join(os.path.dirname(__file__), "..", "..", "test_voice.html")
    return FileResponse(test_html)


@router.get("/prototype")
async def serve_prototype():
    """Sirve el prototipo principal MySherpas-prototype.html bajo el mismo origen."""
    proto_html = os.path.join(os.path.dirname(__file__), "..", "..", "MySherpas-prototype.html")
    return FileResponse(proto_html)


@router.get("/api/cases")
async def list_all_cases():
    """
    Devuelve las 4 familias disponibles con sus IDs cortos ('weah', 'carter', 'johnson', 'lewis')
    y largos ('timothy-melanie-weah', etc.), score, voz asignada y si aplica Modo Pareja.
    """
    results = []
    for full_id, short_id in SHORT_ID_MAP.items():
        ctx = await get_compact_client_context(full_id)
        vp = resolve_voice_profile(full_id, ctx)
        adults_names = " & ".join(a.get("first_name", "") for a in ctx["adults"])
        fh_case = ctx.get("household") or {}
        results.append(
            {
                "client_id": full_id,
                "short_id": short_id,
                "household_name": adults_names,
                "city": fh_case.get("city", ""),
                "state": fh_case.get("state", ""),
                "is_couple": ctx["is_couple"],
                "members": [a.get("first_name") for a in ctx["adults"]],
                "score": ctx["score_summary"].get("published_score"),
                "band": ctx["score_summary"].get("band"),
                "voice_style": vp["style_key"],
                "voice_label": vp["style_label"],
                "gemini_voice": vp["gemini_voice"],
            }
        )
    return {"cases": results}


@router.get("/api/path/{client_id}", response_model=PathSchema)
async def get_client_path(client_id: str):
    """
    Devuelve el Mapa de Viaje completo: niveles gamificados, paradas de metas vitales,
    indicador GPS actual y datos del Modo Multijugador Familiar.
    """
    return await build_gamified_path(client_id)


@router.post("/api/path/{client_id}/milestone", response_model=PathSchema)
async def update_client_milestone(client_id: str, body: MilestoneUpdateRequest):
    """
    Marca un nivel como 'completado' (o 'en_progreso'/'bloqueado'/'needs_review'),
    sube el Score real, dispara la micro-victoria con confeti y genera un 'Choca esos cinco' en pareja.
    """
    return await update_milestone_state(
        client_id,
        body.nivel_id,
        body.estado,
        completed_by=body.completed_by,
    )


@router.post("/api/path/{client_id}/reset", response_model=PathSchema)
async def reset_path_progress(client_id: str):
    """Reinicia el progreso de los niveles y el Score de la familia a su estado inicial."""
    return await reset_client_path(client_id)


@router.get("/api/simulator/{client_id}", response_model=SimulatorResponse)
async def get_simulator_defaults(client_id: str):
    """Obtiene las tarjetas de decisión Power-Up y la Máquina del Tiempo para la familia."""
    return await run_what_if_simulator(client_id)


@router.post("/api/simulator/{client_id}", response_model=SimulatorResponse)
async def calculate_what_if_scenario(client_id: str, body: SimulatorRequest):
    """Calcula en vivo las sinergias de Score, candados desbloqueados y la Máquina del Tiempo al activar Power-Ups."""
    return await run_what_if_simulator(client_id, active_ids=body.active_ids)


@router.get("/api/mentor/insights/{client_id}", response_model=MentorInsightsResponse)
async def get_proactive_mentor_and_jargon(client_id: str):
    """
    Devuelve la notificación proactiva del Mentor IA ('Píldora del día') y las tarjetas
    del Traductor de Jerga explicadas con metáforas cotidianas.
    """
    return await get_mentor_insights(client_id)


@router.get("/api/story/{client_id}", response_model=StorySchema)
async def get_client_story(client_id: str):
    """
    Endpoint para el compañero del Vídeo Introductorio ('Your Financial Story'):
    Devuelve las 4 escenas personalizadas con cifras reales, guion narrado y el CTA al Nivel 1.
    """
    return await build_financial_story(client_id)


@router.get("/api/couple/{client_id}")
async def get_client_couple_mode(client_id: str):
    """
    Devuelve el estado completo del Modo Multijugador Familiar:
    perfiles individuales de la pareja, puente de consenso, Vista Segura para Hijos y muro de High-Fives.
    """
    path_data = await build_gamified_path(client_id)
    raw_couple = await get_couple_dynamics(client_id)
    return {
        **raw_couple,
        "kids_safe_view": path_data.couple_info.kids_safe_view if path_data.couple_info else [],
        "high_fives": path_data.couple_info.high_fives if path_data.couple_info else [],
    }


@router.post("/api/couple/{client_id}/high-five", response_model=CoupleOverview)
async def send_family_high_five(client_id: str, body: HighFiveRequest):
    """Envía un '¡Choca esos cinco! 👋' entre los miembros de la pareja y actualiza el muro familiar."""
    return await add_high_five(
        client_id=client_id,
        from_member=body.from_member,
        to_member=body.to_member,
        milestone_title=body.milestone_title,
        message=body.message or "¡Choca esos cinco! 👋",
    )


@router.post("/api/voice/ask")
async def ask_voice_agent(query: VoiceQuery, request: Request):
    """
    Endpoint HTTP tradicional con gemini-3.5-flash-lite + get_case + ElevenLabs (con caché de MP3).
    """
    case_id = normalize_case_id(query.client_id)
    compact_context, brief = await asyncio.gather(
        get_compact_client_context(case_id),
        build_realtime_brief(case_id, partner=query.partner, topic=query.topic),
    )
    style_override = None if query.style == "auto" else query.style
    voice_profile = resolve_voice_profile(case_id, compact_context, style_override=style_override)

    texto_ia, mcp_usado, claves_consultadas = await ask_llm_with_tools(
        client_id=case_id,
        question=query.question,
        brief=brief,
        voice_profile=voice_profile,
    )

    _, ruta_archivo = await synthesize_elevenlabs_speech(texto_ia, voice_profile)
    base_url = str(request.base_url).rstrip("/")

    return {
        "status": "success",
        "client_id": case_id,
        "short_id": get_short_id(case_id),
        "mcp_usado": mcp_usado,
        "voz_seleccionada": voice_profile["voice_name"],
        "estilo_asesor": voice_profile["style_label"],
        "partner_mode": query.partner,
        "claves_consultadas": claves_consultadas,
        "respuesta_ia": texto_ia,
        "audio_url": f"{base_url}/{ruta_archivo}",
    }
