"""
routes/ws.py
------------
Controlador de conexiones WebSocket:
- WS /ws/voice/{client_id}: Expone el canal bidireccional de voz en tiempo real
  para conversar con baja latencia (<1s) y delega la sesión en realtime_handler.
"""

import os

from fastapi import APIRouter, WebSocket
from services.realtime_handler import handle_realtime_websocket

router = APIRouter()

@router.websocket("/ws/voice/{client_id}")
async def voice_realtime_agent(websocket: WebSocket, client_id: str):
    """
    Canal bidireccional de voz en tiempo real (< 1 segundo de latencia)
    usando Gemini Live / OpenAI Realtime.
    """
    allowed_origin = os.getenv("VOICE_ALLOWED_ORIGIN", "").strip()
    if allowed_origin and websocket.headers.get("origin") != allowed_origin:
        await websocket.close(code=1008, reason="Origin not allowed")
        return
    await handle_realtime_websocket(websocket, client_id)
