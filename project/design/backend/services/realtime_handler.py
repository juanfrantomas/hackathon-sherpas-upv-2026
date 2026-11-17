"""
services/realtime_handler.py
----------------------------
Manejador de sesiones de voz en tiempo real bidireccionales (< 1s de latencia).
- Conecta por WebSocket con el proxy de IA (Gemini Live / OpenAI Realtime).
- Soporta Modo Pareja (`?partner=auto|both|timothy|melanie|daniel|emily`) y foco de hito (`?topic=...`).
- Optimiza el rendimiento reutilizando el contexto SSL global y haciendo fast-forward de paquetes
  de audio sin parsear JSON innecesariamente en Python.
- Protege los tokens compactando las respuestas de `get_case` y omitiendo instrucciones de tools cuando no aplican.
"""

import ssl
import json
import asyncio
from typing import Any, Dict, Optional
import certifi
import websockets
from fastapi import WebSocket, WebSocketDisconnect

from config import WS_BASE_URL, TEAM_KEY, VALID_REALTIME_MODELS
from mcp_client import (
    normalize_case_id,
    get_compact_client_context,
    get_couple_dynamics,
    build_realtime_brief,
    get_section,
)
from services.voice_profiles import resolve_voice_profile
from services.ai_service import REALTIME_TOOLS

# Contexto TLS global reutilizable (evita leer cacert.pem de disco en cada sesión)
_SSL_CTX = ssl.create_default_context(cafile=certifi.where())


def _compose_instructions(
    voice_profile: Dict[str, str],
    brief: str,
    include_tools: bool,
) -> str:
    """Construye las instrucciones del sistema ajustadas al modelo y perfil."""
    tool_rule = (
        "\n4. Si el cliente pide un detalle técnico concreto que no está en tu chuleta (ej. tickers de ETFs en 'positions' o año exacto en 'projections'), usa `get_case` con `sub_section` y explícalo sin tecnicismos."
        if include_tools
        else ""
    )
    return (
        "Eres el asesor financiero en vivo de Sherpas Wealth, cercano, empático y claro.\n\n"
        f"{voice_profile['tone_instructions']}\n\n"
        "REGLAS ESTRICTAS DE CONVERSACIÓN HABLADA:\n"
        "1. PROHIBIDO recitar listas de cifras, porcentajes o decimales. Usa los datos de abajo como tu chuleta interna y tradúcelos a ideas humanas y comparaciones cotidianas.\n"
        "2. Sé breve y dinámico: máximo 2 o 3 frases por turno. Si el cliente te interrumpe, cállate al instante y responde a su nueva duda.\n"
        f"3. Habla siempre en español de España.{tool_rule}\n\n"
        f"CHULETA INTERNA DEL CLIENTE:\n{brief}"
    )


async def handle_realtime_websocket(websocket: WebSocket, client_id: str):
    """
    Gestiona la sesión bidireccional de voz en tiempo real (<1s) entre el navegador
    y el proxy de Sherpas (Gemini Live / OpenAI Realtime).
    """
    await websocket.accept()
    case_id = normalize_case_id(client_id)

    model = websocket.query_params.get("model", "gemini-3.8-live")
    if model not in VALID_REALTIME_MODELS:
        model = "gemini-3.8-live"

    style_override: Optional[str] = websocket.query_params.get("style")
    if style_override == "auto":
        style_override = None

    partner_mode: Optional[str] = websocket.query_params.get("partner", "auto")
    topic: Optional[str] = websocket.query_params.get("topic")
    auto_greet: bool = websocket.query_params.get("greet", "0") in ("1", "true")

    proxy_ws_url = f"{WS_BASE_URL}/realtime?model={model}"

    try:
        compact_context, brief, couple_data = await asyncio.gather(
            get_compact_client_context(case_id),
            build_realtime_brief(case_id, partner=partner_mode, topic=topic),
            get_couple_dynamics(case_id),
        )
        voice_profile = resolve_voice_profile(case_id, compact_context, style_override=style_override)
    except Exception as e:
        print(f"⚠️ Error preparando brief de {case_id}: {e}")
        compact_context = {}
        couple_data = {"is_couple": False, "members": [], "consensus_bridge": ""}
        voice_profile = resolve_voice_profile(case_id, {}, style_override=style_override)
        brief = f"Cliente: {case_id}"

    is_openai = model.startswith("gpt-")
    chosen_voice = voice_profile["openai_voice"] if is_openai else voice_profile["gemini_voice"]
    base_instructions = _compose_instructions(voice_profile, brief, include_tools=is_openai)

    headers = {"Authorization": f"Bearer {TEAM_KEY}"}

    try:
        async with websockets.connect(proxy_ws_url, additional_headers=headers, ssl=_SSL_CTX) as llm_ws:
            print(
                f"✅ [{model}] Realtime conectado para {case_id} | "
                f"Voz={chosen_voice} | Estilo={voice_profile['style_label']} | Partner={partner_mode}"
            )

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
                    "client_id": case_id,
                    "model": model,
                    "voice": chosen_voice,
                    "style_key": voice_profile["style_key"],
                    "style": voice_profile["style_label"],
                    "partner_mode": partner_mode,
                    "is_couple": couple_data.get("is_couple", False),
                    "couple_members": couple_data.get("members", []),
                    "topic": topic,
                    "score": compact_context.get("score_summary"),
                    "message": (
                        f"Conectado con voz '{chosen_voice}' · Registro: {voice_profile['style_label']}."
                    ),
                }
            )

            # Si el usuario entra desde un hito concreto con greet=1, el mentor saluda proactivamente en 1 frase
            if auto_greet and topic:
                await llm_ws.send(
                    json.dumps(
                        {
                            "type": "conversation.item.create",
                            "item": {
                                "type": "message",
                                "role": "user",
                                "content": [
                                    {
                                        "type": "input_text",
                                        "text": f"Acabo de abrir este paso de mi plan: '{topic}'. Explícamelo en 2 frases cercanas.",
                                    }
                                ],
                            },
                        }
                    )
                )
                await llm_ws.send(json.dumps({"type": "response.create"}))

            # Carril A: Frontend -> Proxy
            async def forward_frontend_to_llm():
                nonlocal base_instructions, partner_mode, topic
                try:
                    while True:
                        raw = await websocket.receive_text()

                        # Fast-path: no parsear JSON en Python para los ~12 paquetes de audio/segundo
                        if '"input_audio_buffer.append"' in raw:
                            await llm_ws.send(raw)
                            continue

                        data = json.loads(raw)
                        msg_type = data.get("type", "")

                        if msg_type == "input_audio":
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

                        elif msg_type == "switch_partner":
                            # Permite cambiar en vivo entre 'both', 'timothy', 'melanie', etc. sin reconectar
                            partner_mode = data.get("partner", "both")
                            new_brief = await build_realtime_brief(case_id, partner=partner_mode, topic=topic)
                            base_instructions = _compose_instructions(
                                voice_profile, new_brief, include_tools=is_openai
                            )
                            await llm_ws.send(
                                json.dumps(
                                    {
                                        "type": "session.update",
                                        "session": {"type": "realtime", "instructions": base_instructions},
                                    }
                                )
                            )
                            await websocket.send_json(
                                {
                                    "type": "partner_switched",
                                    "partner_mode": partner_mode,
                                }
                            )

                        elif msg_type == "session.update":
                            ev_session = data.get("session", {})
                            custom_inst = ev_session.get("instructions", "")
                            if base_instructions not in custom_inst:
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

            # Carril B: Proxy -> Frontend (con Tool Calling get_case compacto)
            async def forward_llm_to_frontend():
                try:
                    while True:
                        mensaje_ia = await llm_ws.recv()

                        # Fast-path: el 99% de eventos son deltas de audio/transcripción; reenviarlos sin json.loads
                        if "function_call_arguments.done" not in mensaje_ia:
                            await websocket.send_text(mensaje_ia)
                            continue

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
                                print(f"🔍 [Realtime Tool Call] {case_id} -> {etiqueta}")

                                await websocket.send_json({"type": "tool_call", "section": etiqueta})

                                try:
                                    datos = await get_section(
                                        case_id,
                                        part,
                                        section,
                                        sub_section=sub_section,
                                        compact_for_llm=True,
                                    )
                                    out_str = (
                                        json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
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
        print(f"🔌 El cliente cerró la conexión en el navegador ({case_id}).")
    except Exception as e:
        print(f"🚨 Error en el WebSocket Realtime ({case_id}): {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
