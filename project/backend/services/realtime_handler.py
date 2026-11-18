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

import io
import ssl
import wave
import json
import base64
import asyncio
from typing import Any, Dict, Optional
import certifi
import websockets
from fastapi import WebSocket, WebSocketDisconnect

from config import WS_BASE_URL, TEAM_KEY, ELEVENLABS_API_KEY, VALID_REALTIME_MODELS, llm_client
from mcp_client import (
    normalize_case_id,
    get_compact_client_context,
    get_couple_dynamics,
    build_realtime_brief,
    get_section,
)
from services.voice_profiles import resolve_voice_profile, detect_user_language
from services.ai_service import REALTIME_TOOLS, synthesize_elevenlabs_speech

# Contexto TLS global reutilizable (evita leer cacert.pem de disco en cada sesión)
_SSL_CTX = ssl.create_default_context(cafile=certifi.where())


async def _transcribe_user_pcm_async(pcm_bytes: bytes, websocket: WebSocket) -> None:
    """
    Transcribe en segundo plano (sin añadir latencia a la respuesta de voz) lo que dijo el
    cliente cuando usa Gemini Live y el navegador no envió transcripción local, para mostrar
    su burbuja en el chat estilo WhatsApp.
    """
    if len(pcm_bytes) < 4800:  # Menos de ~0.1s de audio a 24kHz PCM16
        return
    try:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(pcm_bytes)
        wav_data = buf.getvalue()
        resp = await llm_client.audio.transcriptions.create(
            model="scribe-v2",
            file=("user_turn.wav", wav_data, "audio/wav"),
        )
        txt = (getattr(resp, "text", None) or "").strip()
        if txt:
            await websocket.send_json({"type": "user_transcript", "text": txt})
    except Exception:
        pass


def _compose_instructions(
    voice_profile: Dict[str, str],
    brief: str,
    include_tools: bool,
) -> str:
    """Construye las instrucciones del sistema ajustadas al modelo y perfil."""
    tool_rule = (
        "\n5. Si el cliente pide un detalle técnico concreto que no está en tu chuleta (ej. tickers de ETFs en 'positions' o año exacto en 'projections'), usa `get_case` con `sub_section` y explícalo sin tecnicismos."
        if include_tools
        else ""
    )
    return (
        "Eres el asesor financiero en vivo de Sherpas Wealth, cercano, empático, optimista y claro.\n\n"
        f"{voice_profile['tone_instructions']}\n\n"
        "REGLAS ESTRICTAS DE CONVERSACIÓN HABLADA Y EMPATÍA EMOCIONAL:\n"
        "1. SUAVIZAR NOTICIAS DIFÍCILES (CERO MIEDO): Las malas noticias hacen que la gente aparte la vista en vez de actuar. NUNCA uses palabras alarmistas como 'crítico', 'momento crítico', 'peligro', 'gastas más de lo que ingresas', 'muerte', 'fallecimiento' ni 'quedarte sin dinero'. Si el Score es bajo (como el 26 de Michael), destaca primero su gran capacidad de ahorro y preséntalo con suavidad como un simple ajuste de calendario entre sus metas. Si hablas de seguro de vida (como Daniel y Emily), exprésalo siempre como 'una red de tranquilidad para los sueños de los niños'.\n"
        "2. VELOCIDAD Y RITMO: Habla a velocidad normal, tranquila y conversacional, con naturalidad y calidez.\n"
        "3. BREVEDAD: Máximo 2 frases cortas y directas por turno. Ve directo al grano sin rodeos ni introducciones largas. Si el cliente te interrumpe, cállate al instante.\n"
        "4. Si el usuario habla en español, responde SIEMPRE con acento, entonación y cadencia 100% española nativa (castellano peninsular), NUNCA con acento inglés o extranjero, incluso al pronunciar nombres propios o cuentas como 401k."
        f"{tool_rule}\n\n"
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
    mic_mode: str = websocket.query_params.get("mic_mode", "ptt")

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
                f"Voz={chosen_voice} | ModoMic={mic_mode} | Estilo={voice_profile['style_label']} | Partner={partner_mode}"
            )

            turn_detection_cfg = (
                None
                if mic_mode == "ptt"
                else {"type": "server_vad", "silence_duration_ms": 650}
            )

            audio_config: Dict[str, Any] = {
                "input": {
                    "format": {"type": "audio/pcm", "rate": 24000},
                    "turn_detection": turn_detection_cfg,
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

            use_elevenlabs = websocket.query_params.get("tts", "elevenlabs") != "native"
            display_voice = voice_profile["voice_name"] if use_elevenlabs else chosen_voice

            await websocket.send_json(
                {
                    "type": "session_ready",
                    "client_id": case_id,
                    "model": model,
                    "voice": display_voice,
                    "mic_mode": mic_mode,
                    "speech_speed": voice_profile.get("speech_speed", 1.0),
                    "style_key": voice_profile["style_key"],
                    "style": voice_profile["style_label"],
                    "partner_mode": partner_mode,
                    "is_couple": couple_data.get("is_couple", False),
                    "couple_members": couple_data.get("members", []),
                    "topic": topic,
                    "score": compact_context.get("score_summary"),
                    "message": (
                        f"Conectado con voz '{display_voice}' · Registro: {voice_profile['style_label']}."
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
            active_lang = voice_profile.get("detected_language", "es")

            async def forward_frontend_to_llm():
                nonlocal base_instructions, partner_mode, topic, voice_profile, chosen_voice, active_lang
                user_pcm_buffer = bytearray()
                try:
                    while True:
                        raw = await websocket.receive_text()

                        # Fast-path: paquetes de audio base64
                        if '"input_audio_buffer.append"' in raw:
                            await llm_ws.send(raw)
                            if not is_openai and len(user_pcm_buffer) < 24000 * 2 * 25:
                                try:
                                    b64_part = raw.split('"audio":"', 1)[1].split('"', 1)[0]
                                    user_pcm_buffer.extend(base64.b64decode(b64_part))
                                except Exception:
                                    pass
                            continue

                        data = json.loads(raw)
                        msg_type = data.get("type", "")

                        if msg_type == "input_audio":
                            b64_audio = data.get("audio_b64", "")
                            await llm_ws.send(
                                json.dumps(
                                    {
                                        "type": "input_audio_buffer.append",
                                        "audio": b64_audio,
                                    }
                                )
                            )
                            if not is_openai and b64_audio:
                                try:
                                    user_pcm_buffer.extend(base64.b64decode(b64_audio))
                                except Exception:
                                    pass
                        elif msg_type == "end_of_speech":
                            await llm_ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
                            await llm_ws.send(json.dumps({"type": "response.create"}))
                            if not is_openai and user_pcm_buffer and not data.get("has_local_transcript"):
                                pcm_copy = bytes(user_pcm_buffer)
                                user_pcm_buffer.clear()
                                asyncio.create_task(_transcribe_user_pcm_async(pcm_copy, websocket))
                            else:
                                user_pcm_buffer.clear()

                        elif msg_type in ("user_text", "question"):
                            texto = (data.get("text") or data.get("question") or "").strip()
                            if texto:
                                # Solo cambiar la voz si el usuario ha cambiado de idioma ('es' <-> 'en')
                                new_lang = detect_user_language(texto, client_id=case_id)
                                if new_lang != active_lang:
                                    active_lang = new_lang
                                    voice_profile = resolve_voice_profile(
                                        case_id,
                                        compact_context,
                                        style_override=style_override,
                                        user_text=texto,
                                    )
                                    chosen_voice = (
                                        voice_profile["openai_voice"]
                                        if is_openai
                                        else voice_profile["gemini_voice"]
                                    )
                                    base_instructions = _compose_instructions(
                                        voice_profile, brief, include_tools=is_openai
                                    )
                                    await llm_ws.send(
                                        json.dumps(
                                            {
                                                "type": "session.update",
                                                "session": {
                                                    "type": "realtime",
                                                    "instructions": base_instructions,
                                                    "audio": {"output": {"voice": chosen_voice}},
                                                },
                                            }
                                        )
                                    )
                                    await websocket.send_json(
                                        {
                                            "type": "voice_changed_for_language",
                                            "language": active_lang,
                                            "voice": voice_profile["voice_name"] if use_elevenlabs else chosen_voice,
                                        }
                                    )

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

            # Carril B: Proxy -> Frontend (con Tool Calling get_case compacto y voz ElevenLabs)
            async def forward_llm_to_frontend():
                bot_turn_text = ""
                try:
                    while True:
                        mensaje_ia = await llm_ws.recv()

                        # Fast-path solo cuando NO usamos ElevenLabs
                        if not use_elevenlabs and "function_call_arguments.done" not in mensaje_ia:
                            await websocket.send_text(mensaje_ia)
                            continue

                        evento_ia = json.loads(mensaje_ia)
                        ev_type = evento_ia.get("type", "")

                        if use_elevenlabs:
                            # Suprimimos el audio PCM robótico nativo del modelo porque lo hablaremos con ElevenLabs
                            if ev_type in ("audio_delta", "response.output_audio.delta", "response.audio.delta"):
                                continue
                            if ev_type == "response.created":
                                bot_turn_text = ""
                            elif ev_type in (
                                "transcript_delta",
                                "response.output_audio_transcript.delta",
                                "response.audio_transcript.delta",
                            ):
                                bot_turn_text += evento_ia.get("text") or evento_ia.get("delta") or ""
                            elif ev_type in (
                                "response.output_audio_transcript.done",
                                "response.audio_transcript.done",
                            ):
                                full_t = (evento_ia.get("transcript") or "").strip()
                                if full_t and not bot_turn_text.strip():
                                    bot_turn_text = full_t
                            elif ev_type == "response.done":
                                clean_text = bot_turn_text.strip()
                                bot_turn_text = ""
                                if clean_text:
                                    try:
                                        _, data_uri = await synthesize_elevenlabs_speech(clean_text, voice_profile)
                                        await websocket.send_json(
                                            {
                                                "type": "elevenlabs_audio",
                                                "audio_url": data_uri,
                                                "voice": voice_profile["voice_name"],
                                                "speech_speed": voice_profile.get("speech_speed", 1.0),
                                            }
                                        )
                                    except Exception as tts_err:
                                        print(f"⚠️ Error sintetizando ElevenLabs en WS: {tts_err}")

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
