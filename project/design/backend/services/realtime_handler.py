"""
services/realtime_handler.py
----------------------------
Manejador de sesiones de voz en tiempo real bidireccionales (< 1s de latencia).
- Conecta por WebSocket con el proxy de IA (Gemini Live / OpenAI Realtime).
- Inyecta el brief ligero de ~850 tokens y las directrices de registro lingüístico
  (informal/callejero, refranero, sencillo o formal) y voz nativa al inicio.
- Reenvía el audio en streaming (PCM16 24kHz) y gestiona cortes e interrupciones (barge-in).
- Maneja llamadas a herramientas en vivo (Tool Calling de `get_case`) si el cliente pide detalles profundos.
"""

import ssl
import json
import asyncio
from typing import Any, Dict
import certifi
import websockets
from fastapi import WebSocket, WebSocketDisconnect

from config import WS_BASE_URL, TEAM_KEY, VALID_REALTIME_MODELS
from mcp_client import get_compact_client_context, build_realtime_brief, get_section
from services.voice_profiles import resolve_voice_profile
from services.ai_service import REALTIME_TOOLS


async def handle_realtime_websocket(websocket: WebSocket, client_id: str):
    """
    Gestiona la sesión bidireccional de voz en tiempo real (<1s) entre el navegador
    y el proxy de Sherpas (Gemini Live / OpenAI Realtime).
    """
    await websocket.accept()

    model = websocket.query_params.get("model", "gemini-3.8-live")
    if model not in VALID_REALTIME_MODELS:
        model = "gemini-3.8-live"

    style_override = websocket.query_params.get("style")
    if style_override == "auto":
        style_override = None

    proxy_ws_url = f"{WS_BASE_URL}/realtime?model={model}"

    try:
        compact_context = await get_compact_client_context(client_id)
        voice_profile = resolve_voice_profile(client_id, compact_context, style_override=style_override)
        brief = await build_realtime_brief(client_id)
    except Exception as e:
        print(f"⚠️ Error preparando brief de {client_id}: {e}")
        compact_context = {}
        voice_profile = resolve_voice_profile(client_id, {}, style_override=style_override)
        brief = f"Cliente: {client_id}"

    is_openai = model.startswith("gpt-")
    chosen_voice = voice_profile["openai_voice"] if is_openai else voice_profile["gemini_voice"]

    base_instructions = (
        "Eres el asesor financiero en vivo de Sherpas Wealth, pero NO hablas como un banco aburrido.\n\n"
        f"{voice_profile['tone_instructions']}\n\n"
        "REGLAS ESTRICTAS DE CONVERSACIÓN HABLADA:\n"
        "1. PROHIBIDO aburrir con listas de cifras, porcentajes o decimales. El resumen numérico de abajo es SOLO tu chuleta interna para saber qué le pasa al cliente; tradúcelo a ideas humanas, refranes y comparaciones de la vida real.\n"
        "2. Sé breve y dinámico: máximo 2 o 3 frases por respuesta. Si el cliente te interrumpe, cállate al instante y síguele el rollo.\n"
        "3. Habla siempre en español de España (a menos que el cliente te hable en otro idioma).\n"
        "4. Si el cliente te pide un detalle muy concreto que no está en tu chuleta (como qué acciones o ETFs tiene exactamente), usa la herramienta `get_case` pero explícalo con el mismo estilo y sin soltar rollos técnicos.\n\n"
        f"CHULETA INTERNA DEL CLIENTE (NO LEER COMO UN ROBOT):\n{brief}"
    )

    headers = {"Authorization": f"Bearer {TEAM_KEY}"}
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())

    try:
        async with websockets.connect(proxy_ws_url, additional_headers=headers, ssl=ssl_ctx) as llm_ws:
            print(
                f"✅ [{model}] Realtime conectado para {client_id} | "
                f"Voz={chosen_voice} | Estilo={voice_profile['style_label']}"
            )

            # Configuración de audio y voz nativa (tanto para Gemini Live como para OpenAI Realtime)
            audio_config: Dict[str, Any] = {
                "input": {
                    "format": {"type": "audio/pcm", "rate": 24000},
                    "turn_detection": {"type": "server_vad", "silence_duration_ms": 500},
                },
                "output": {
                    "format": {"type": "audio/pcm", "rate": 24000},
                    "voice": chosen_voice,
                },
            }
            if is_openai:
                audio_config["input"]["transcription"] = {"model": "gpt-4o-mini-transcribe"}

            session_payload: Dict[str, Any] = {
                "type": "realtime",
                "instructions": base_instructions,
                "audio": audio_config,
            }
            if is_openai:
                session_payload["tools"] = REALTIME_TOOLS
                session_payload["tool_choice"] = "auto"

            await llm_ws.send(json.dumps({"type": "session.update", "session": session_payload}))

            await websocket.send_json(
                {
                    "type": "session_ready",
                    "client_id": client_id,
                    "model": model,
                    "voice": chosen_voice,
                    "style_key": voice_profile["style_key"],
                    "style": voice_profile["style_label"],
                    "score": compact_context.get("score_summary"),
                    "message": (
                        f"Conectado con voz '{chosen_voice}' · Registro: {voice_profile['style_label']}."
                    ),
                }
            )

            # Carril A: Frontend -> Proxy
            async def forward_frontend_to_llm():
                try:
                    while True:
                        raw = await websocket.receive_text()
                        data = json.loads(raw)
                        msg_type = data.get("type", "")

                        if msg_type == "input_audio_buffer.append":
                            await llm_ws.send(raw)
                        elif msg_type == "input_audio":
                            await llm_ws.send(
                                json.dumps(
                                    {
                                        "type": "input_audio_buffer.append",
                                        "audio": data["audio_b64"],
                                    }
                                )
                            )
                        elif msg_type == "end_of_speech":
                            await llm_ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
                            await llm_ws.send(json.dumps({"type": "response.create"}))

                        elif msg_type in ("user_text", "question"):
                            texto = (data.get("text") or data.get("question") or "").strip()
                            if texto:
                                await llm_ws.send(
                                    json.dumps(
                                        {
                                            "type": "conversation.item.create",
                                            "item": {
                                                "type": "message",
                                                "role": "user",
                                                "content": [{"type": "input_text", "text": texto}],
                                            },
                                        }
                                    )
                                )
                                await llm_ws.send(json.dumps({"type": "response.create"}))

                        elif msg_type == "session.update":
                            ev_session = data.get("session", {})
                            custom_inst = ev_session.get("instructions", "")
                            ev_session["instructions"] = f"{custom_inst}\n\n{base_instructions}".strip()
                            ev_session.setdefault("audio", {}).setdefault("output", {})["voice"] = chosen_voice
                            if is_openai:
                                ev_session["tools"] = REALTIME_TOOLS
                            data["session"] = ev_session
                            await llm_ws.send(json.dumps(data))

                        else:
                            await llm_ws.send(raw)

                except WebSocketDisconnect:
                    pass

            # Carril B: Proxy -> Frontend (con Tool Calling get_case)
            async def forward_llm_to_frontend():
                try:
                    while True:
                        mensaje_ia = await llm_ws.recv()
                        evento_ia = json.loads(mensaje_ia)
                        ev_type = evento_ia.get("type", "")

                        if ev_type == "response.function_call_arguments.done":
                            call_id = evento_ia.get("call_id")
                            fn_name = evento_ia.get("name")
                            if fn_name == "get_case" and call_id:
                                args = json.loads(evento_ia.get("arguments") or "{}")
                                part = args.get("part", "financial-health")
                                section = args.get("section", "score")
                                sub_section = args.get("sub_section")
                                etiqueta = f"{part}.{section}" + (f".{sub_section}" if sub_section else "")
                                print(f"🔍 [Realtime Tool Call] {client_id} -> {etiqueta}")

                                await websocket.send_json({"type": "tool_call", "section": etiqueta})

                                try:
                                    datos = await get_section(client_id, part, section, sub_section=sub_section)
                                    out_str = (
                                        json.dumps(datos, ensure_ascii=False)
                                        if not isinstance(datos, str)
                                        else datos
                                    )
                                except Exception as e:
                                    out_str = json.dumps({"error": str(e)})

                                await llm_ws.send(
                                    json.dumps(
                                        {
                                            "type": "conversation.item.create",
                                            "item": {
                                                "type": "function_call_output",
                                                "call_id": call_id,
                                                "output": out_str,
                                            },
                                        }
                                    )
                                )
                                await llm_ws.send(json.dumps({"type": "response.create"}))
                            continue

                        # Reenvío limpio del evento nativo
                        await websocket.send_text(mensaje_ia)

                except Exception as e:
                    print(f"🔌 Desconexión de la IA Realtime: {e}")

            tarea_frontend = asyncio.create_task(forward_frontend_to_llm())
            tarea_ia = asyncio.create_task(forward_llm_to_frontend())

            done, pending = await asyncio.wait(
                [tarea_frontend, tarea_ia],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for t in pending:
                t.cancel()

    except WebSocketDisconnect:
        print(f"🔌 El cliente cerró la conexión en el navegador ({client_id}).")
    except Exception as e:
        print(f"🚨 Error en el WebSocket Realtime ({client_id}): {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
