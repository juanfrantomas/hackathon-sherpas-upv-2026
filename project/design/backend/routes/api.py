"""
routes/api.py
-------------
Controlador de rutas HTTP REST de la API:
- GET /: Sirve el probador visual de voz (test_voice.html).
- GET /api/path/{client_id}: Devuelve los niveles del mapa financiero gamificado.
- POST /api/voice/ask: Endpoint tradicional de pregunta-respuesta de voz (gpt-5-mini + ElevenLabs).
"""

import os
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

from models import PathSchema
from mcp_client import get_compact_client_context, build_realtime_brief
from services.voice_profiles import resolve_voice_profile
from services.ai_service import (
    ask_llm_with_tools,
    synthesize_elevenlabs_speech,
    build_gamified_path,
)

router = APIRouter()

class VoiceQuery(BaseModel):
    client_id: str
    question: str
    style: str = "auto"


@router.get("/")
async def serve_voice_tester():
    """Sirve la página web del probador de voz."""
    test_html = os.path.join(os.path.dirname(__file__), "..", "..", "test_voice.html")
    return FileResponse(test_html)


@router.get("/api/path/{client_id}", response_model=PathSchema)
async def get_client_path(client_id: str):
    """
    Genera el mapa financiero gamificado REAL para el Frontend,
    extrayendo los hitos calculados (top_moves) del plan de esa familia.
    """
    return await build_gamified_path(client_id)


@router.post("/api/voice/ask")
async def ask_voice_agent(query: VoiceQuery):
    """Endpoint HTTP tradicional con gpt-5-mini + get_case + ElevenLabs."""
    compact_context = await get_compact_client_context(query.client_id)
    style_override = None if query.style == "auto" else query.style
    voice_profile = resolve_voice_profile(query.client_id, compact_context, style_override=style_override)
    brief = await build_realtime_brief(query.client_id)

    texto_ia, mcp_usado, claves_consultadas = await ask_llm_with_tools(
        client_id=query.client_id,
        question=query.question,
        brief=brief,
        voice_profile=voice_profile,
    )

    audio_bytes = await synthesize_elevenlabs_speech(texto_ia, voice_profile)
    ruta_archivo = f"assets/respuesta_{query.client_id}.mp3"
    with open(ruta_archivo, "wb") as f:
        f.write(audio_bytes)

    return {
        "status": "success",
        "mcp_usado": mcp_usado,
        "voz_seleccionada": voice_profile["voice_name"],
        "estilo_asesor": voice_profile["style_label"],
        "claves_consultadas": claves_consultadas,
        "respuesta_ia": texto_ia,
        "audio_url": f"http://127.0.0.1:8000/{ruta_archivo}",
    }
