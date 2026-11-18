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
from fastapi import APIRouter, HTTPException, Request
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
    build_compact_mentor_brief,
    SHORT_ID_MAP,
)
from services.voice_profiles import resolve_voice_profile
from services.video_service import (
    get_latest_job_for_client,
    get_video_job,
    list_family_videos,
    start_video_generation,
)
from services.ai_service import (
    ask_llm_with_tools,
    synthesize_elevenlabs_speech,
    start_tts_prefetch,
    get_tts_meta,
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
    include_audio: bool = True


class TtsNarrationRequest(BaseModel):
    client_id: str
    text: str
    style: str = "auto"


class AudioVoiceQuery(BaseModel):
    client_id: str
    audio_b64: Optional[str] = None
    audio_base64: Optional[str] = None
    mime_type: str = "audio/webm"
    style: str = "auto"
    partner: Optional[str] = "auto"
    topic: Optional[str] = None
    include_audio: bool = True


_NO_CACHE_HEADERS = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}


@router.get("/")
async def serve_voice_tester():
    """Sirve la consola interactiva con Voz Realtime y los 5 pilares del producto."""
    test_html = os.path.join(os.path.dirname(__file__), "..", "..", "test_voice.html")
    return FileResponse(test_html, headers=_NO_CACHE_HEADERS)


@router.get("/prototype")
async def serve_prototype():
    """Sirve el prototipo principal MySherpas-prototype.html bajo el mismo origen."""
    proto_html = os.path.join(os.path.dirname(__file__), "..", "..", "MySherpas-prototype.html")
    return FileResponse(proto_html, headers=_NO_CACHE_HEADERS)


@router.get("/mobile")
async def serve_mobile_app():
    """Sirve la versión móvil dedicada (mobile.html)."""
    mob_html = os.path.join(os.path.dirname(__file__), "..", "..", "mobile.html")
    return FileResponse(mob_html, headers=_NO_CACHE_HEADERS)


@router.get("/videos/{filename}")
async def serve_family_video(filename: str):
    """Sirve el vídeo de 1.5-2 min preparado para cada familia desde project/videos/ o project/."""
    from fastapi import HTTPException

    safe_name = os.path.basename(filename)
    base_project = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    candidates = [
        os.path.join(base_project, "videos", safe_name),
        os.path.join(base_project, safe_name),
        os.path.join(base_project, "..", "assets", safe_name),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return FileResponse(path, media_type="video/mp4")
    raise HTTPException(status_code=404, detail=f"Video {safe_name} no encontrado en project/videos/")


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
    Endpoint HTTP con gemini-3.5-flash-lite + brief compacto (<280 tokens, ~1.0s)
    + prefetch en paralelo hacia ElevenLabs Multilingual v2 con API Key personal.
    """
    case_id = normalize_case_id(query.client_id)
    compact_context, brief = await asyncio.gather(
        get_compact_client_context(case_id),
        build_compact_mentor_brief(case_id, partner=query.partner, topic=query.topic),
    )
    style_override = None if query.style == "auto" else query.style
    voice_profile = resolve_voice_profile(
        case_id,
        compact_context,
        style_override=style_override,
        user_text=query.question,
    )

    texto_ia, mcp_usado, claves_consultadas = await ask_llm_with_tools(
        client_id=case_id,
        question=query.question,
        brief=brief,
        voice_profile=voice_profile,
    )

    data_uri = ""
    if query.include_audio and texto_ia:
        _, data_uri = await synthesize_elevenlabs_speech(texto_ia, voice_profile)
    elif texto_ia:
        start_tts_prefetch(texto_ia, voice_profile)

    tts_meta = get_tts_meta(texto_ia, voice_profile) if texto_ia else {}

    return {
        "status": "success",
        "client_id": case_id,
        "short_id": get_short_id(case_id),
        "mcp_usado": mcp_usado,
        "idioma_detectado": voice_profile.get("detected_language", "es"),
        "voz_seleccionada": voice_profile["voice_name"],
        "estilo_asesor": voice_profile["style_label"],
        "speech_speed": voice_profile.get("speech_speed", 1.0),
        "tts_provider": tts_meta.get("tts_provider", "elevenlabs_personal_api"),
        "tts_model": tts_meta.get("tts_model", "eleven_multilingual_v2"),
        "partner_mode": query.partner,
        "claves_consultadas": claves_consultadas,
        "respuesta_ia": texto_ia,
        "audio_url": data_uri,
    }


@router.post("/api/tts")
async def synthesize_narration_tts(body: TtsNarrationRequest):
    """
    Sintetiza cualquier respuesta o escena del Vídeo Introductorio ('Your Financial Story')
    con la voz nativa española de ElevenLabs Multilingual v2 usando la API Key personal.
    """
    case_id = normalize_case_id(body.client_id)
    compact_context = await get_compact_client_context(case_id)
    style_override = None if body.style == "auto" else body.style
    voice_profile = resolve_voice_profile(
        case_id,
        compact_context,
        style_override=style_override,
        user_text=body.text,
    )
    _, data_uri = await synthesize_elevenlabs_speech(body.text, voice_profile)
    tts_meta = get_tts_meta(body.text, voice_profile)
    return {
        "status": "success",
        "client_id": case_id,
        "voice_name": voice_profile["voice_name"],
        "style_label": voice_profile["style_label"],
        "speech_speed": voice_profile.get("speech_speed", 1.0),
        "tts_provider": tts_meta.get("tts_provider", "elevenlabs_personal_api"),
        "tts_model": tts_meta.get("tts_model", "eleven_multilingual_v2"),
        "audio_url": data_uri,
    }


@router.post("/api/voice/audio-ask")
async def ask_voice_with_raw_audio(body: AudioVoiceQuery):
    """
    Recibe el audio grabado directamente del micrófono del navegador (en cualquier idioma:
    español, inglés, chino mandarín, francés, etc.), lo transcribe automáticamente con
    detección de idioma (`scribe-v2`), y responde con el mismo idioma y la voz nativa de ElevenLabs
    Multilingual v2 adaptada al perfil psicológico del cliente.
    """
    import base64
    from config import llm_client

    case_id = normalize_case_id(body.client_id)
    raw_b64 = (body.audio_b64 or body.audio_base64 or "").strip()
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]
    if not raw_b64:
        return {
            "status": "empty",
            "transcripcion_usuario": "",
            "transcribed_question": "",
            "respuesta_ia": "",
            "audio_url": "",
        }

    audio_bytes = base64.b64decode(raw_b64)
    ext = "webm"
    if "wav" in (body.mime_type or ""):
        ext = "wav"
    elif "mp4" in (body.mime_type or "") or "m4a" in (body.mime_type or ""):
        ext = "mp4"
    elif "ogg" in (body.mime_type or ""):
        ext = "ogg"

    async def _transcribe() -> str:
        try:
            tr = await llm_client.audio.transcriptions.create(
                model="scribe-v2",
                file=(f"user_voice.{ext}", audio_bytes, body.mime_type or "audio/webm"),
            )
            return (getattr(tr, "text", None) or "").strip()
        except Exception as err:
            print(f"⚠️ Error transcribiendo audio con scribe-v2: {err}")
            return ""

    transcribed_text, compact_context, brief = await asyncio.gather(
        _transcribe(),
        get_compact_client_context(case_id),
        build_compact_mentor_brief(case_id, partner=body.partner, topic=body.topic),
    )

    if not transcribed_text:
        return {
            "status": "empty",
            "transcripcion_usuario": "",
            "transcribed_question": "",
            "respuesta_ia": "",
            "audio_url": "",
        }

    style_override = None if body.style == "auto" else body.style
    voice_profile = resolve_voice_profile(
        case_id,
        compact_context,
        style_override=style_override,
        user_text=transcribed_text,
    )

    texto_ia, mcp_usado, claves_consultadas = await ask_llm_with_tools(
        client_id=case_id,
        question=transcribed_text,
        brief=brief,
        voice_profile=voice_profile,
    )

    data_uri = ""
    if body.include_audio and texto_ia:
        _, data_uri = await synthesize_elevenlabs_speech(texto_ia, voice_profile)
    elif texto_ia:
        start_tts_prefetch(texto_ia, voice_profile)

    tts_meta = get_tts_meta(texto_ia, voice_profile) if texto_ia else {}

    return {
        "status": "success",
        "client_id": case_id,
        "short_id": get_short_id(case_id),
        "transcripcion_usuario": transcribed_text,
        "transcribed_question": transcribed_text,
        "idioma_detectado": voice_profile.get("detected_language", "es"),
        "voz_seleccionada": voice_profile["voice_name"],
        "estilo_asesor": voice_profile["style_label"],
        "speech_speed": voice_profile.get("speech_speed", 1.0),
        "tts_provider": tts_meta.get("tts_provider", "elevenlabs_personal_api"),
        "tts_model": tts_meta.get("tts_model", "eleven_multilingual_v2"),
        "respuesta_ia": texto_ia,
        "audio_url": data_uri,
    }


class VideoGenerateRequest(BaseModel):
    client_id: str = "timothy-melanie-weah"
    demo_mode: Optional[bool] = None
    audio_mode: Optional[str] = None


@router.get("/api/videos")
async def get_all_family_videos():
    """Lista el estado de los vídeos MP4 disponibles para las 4 familias."""
    return {"videos": list_family_videos()}


@router.post("/api/videos/generate", status_code=202)
async def generate_family_video(body: VideoGenerateRequest):
    """Lanza la generación Remotion + ElevenLabs del vídeo para una familia y lo publica en /videos/{short_id}.mp4."""
    try:
        job = await start_video_generation(
            client_id=body.client_id,
            demo_mode=body.demo_mode,
            audio_mode=body.audio_mode,
        )
        return job
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/api/videos/jobs/{job_id}")
async def get_family_video_job(job_id: str):
    """Consulta el progreso de un trabajo de generación de vídeo."""
    job = get_video_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Trabajo de vídeo no encontrado.")
    return job


@router.get("/api/videos/status/{client_id}")
async def get_family_video_status(client_id: str):
    """Devuelve si ya existe el MP4 en /videos/{short_id}.mp4 y el último trabajo lanzado."""
    short_id = get_short_id(client_id)
    videos = {v["short_id"]: v for v in list_family_videos()}
    info = videos.get(short_id, {"exists": False, "video_url": None, "size_bytes": 0})
    return {
        "client_id": normalize_case_id(client_id),
        "short_id": short_id,
        "exists": info["exists"],
        "video_url": info["video_url"],
        "size_bytes": info["size_bytes"],
        "latest_job": get_latest_job_for_client(client_id),
    }
