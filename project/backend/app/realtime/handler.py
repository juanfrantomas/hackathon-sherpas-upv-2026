"""The realtime voice session.

The browser speaks to this backend and the backend relays to the proxy of the
AI.  Two lanes run at the same time: the audio of the household goes up and
the answer of the model comes down.

Two details matter for the latency: the audio packets are forwarded without
being parsed, and the plan is read once when the session opens.
"""

from __future__ import annotations

import json
from typing import Any

from app.domain.voice_profiles import resolve_voice_profile
from app.integration.ai.realtime import AudioConfig, RealtimeProxy
from app.integration.mcp.context import CaseContext, as_json
from app.logging_config import get_logger
from app.services.mentor_service import GET_CASE_PARAM_SCHEMA

logger = get_logger(__name__)

#: The tool the model may call during a live conversation.
REALTIME_TOOLS = [
    {
        "type": "function",
        "name": "get_case",
        "description": (
            "Úsala SOLO si el cliente pide un detalle que no está en el brief "
            "inicial (ej. tickers en 'positions', año concreto en 'projections' "
            "o impuestos en 'taxDragAnalysis')."
        ),
        "parameters": GET_CASE_PARAM_SCHEMA,
    }
]


def compose_instructions(
    voice_profile: dict[str, str], brief: str, *, include_tools: bool
) -> str:
    """The instructions of the session, for the model."""
    tool_rule = (
        "\n4. Si el cliente pide un detalle técnico concreto que no está en tu "
        "chuleta (ej. tickers de ETFs en 'positions' o año exacto en "
        "'projections'), usa `get_case` con `sub_section` y explícalo sin "
        "tecnicismos."
        if include_tools
        else ""
    )
    return (
        "Eres el asesor financiero en vivo de Sherpas Wealth, cercano, empático "
        "y claro.\n\n"
        f"{voice_profile['tone_instructions']}\n\n"
        "REGLAS ESTRICTAS DE CONVERSACIÓN HABLADA:\n"
        "1. PROHIBIDO recitar listas de cifras, porcentajes o decimales. Usa los "
        "datos de abajo como tu chuleta interna y tradúcelos a ideas humanas y "
        "comparaciones cotidianas.\n"
        "2. Sé breve y dinámico: máximo 2 o 3 frases por turno. Si el cliente te "
        "interrumpe, cállate al instante y responde a su nueva duda.\n"
        f"3. Habla siempre en español de España.{tool_rule}\n\n"
        f"CHULETA INTERNA DEL CLIENTE:\n{brief}"
    )


async def handle_realtime_websocket(
    websocket: Any,
    case_id: str,
    *,
    context: CaseContext,
    proxy_base_url: str,
    token: str,
    model: str = "gemini-3.8-live",
    style_override: str | None = None,
    partner_mode: str | None = "auto",
    topic: str | None = None,
    auto_greet: bool = False,
    ssl_context: Any = None,
) -> None:
    """Hold a live conversation with the household."""
    await websocket.accept()

    try:
        household = await context.get_compact_client_context(case_id)
        brief = await context.build_realtime_brief(
            case_id, partner=partner_mode, topic=topic
        )
        couple = await context.get_couple_dynamics(case_id)
    except Exception as exc:  # noqa: BLE001 - the session must still open
        logger.warning("Could not prepare the brief of %s: %s", case_id, exc)
        household = {}
        couple = {"is_couple": False, "members": []}
        brief = f"Cliente: {case_id}"

    voice_profile = resolve_voice_profile(
        household.get("classification"),
        style_override=None if style_override in (None, "auto") else style_override,
    )

    is_openai = model.startswith("gpt-")
    voice = (
        voice_profile["openai_voice"] if is_openai else voice_profile["gemini_voice"]
    )
    instructions = compose_instructions(voice_profile, brief, include_tools=is_openai)

    proxy = RealtimeProxy(
        base_url=proxy_base_url,
        token=token,
        model=model,
        ssl_context=ssl_context,
    )

    try:
        await proxy.connect()
    except Exception as exc:  # noqa: BLE001
        logger.error("The realtime session could not be opened: %s", exc)
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close()
        return

    session_payload: dict[str, Any] = {
        "type": "realtime",
        "instructions": instructions,
        "audio": AudioConfig(
            voice=voice, transcription_model="gpt-4o-mini-transcribe" if is_openai else None
        ).to_payload(),
    }
    if is_openai:
        session_payload["tools"] = REALTIME_TOOLS
        session_payload["tool_choice"] = "auto"

    await proxy.send({"type": "session.update", "session": session_payload})

    await websocket.send_json(
        {
            "type": "session_ready",
            "case_id": case_id,
            "model": model,
            "voice": voice,
            "style_key": voice_profile["style_key"],
            "style": voice_profile["style_label"],
            "partner_mode": partner_mode,
            "is_couple": couple.get("is_couple", False),
            "couple_members": couple.get("members", []),
            "topic": topic,
            "score": household.get("score_summary"),
            "message": (
                f"Conectado con voz '{voice}' · "
                f"Registro: {voice_profile['style_label']}."
            ),
        }
    )

    # The household opened a milestone: the mentor greets it in one sentence.
    if auto_greet and topic:
        await proxy.send(
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                f"Acabo de abrir este paso de mi plan: '{topic}'. "
                                "Explícamelo en 2 frases cercanas."
                            ),
                        }
                    ],
                },
            }
        )
        await proxy.send({"type": "response.create"})

    async def forward_to_proxy() -> None:
        """Lane A: the household speaks, the proxy listens."""
        current_instructions = instructions
        current_partner = partner_mode
        current_topic = topic
        while True:
            raw = await websocket.receive_text()

            # The audio packets are the bulk of the traffic: they are relayed
            # without being parsed.
            if '"input_audio_buffer.append"' in raw:
                await proxy.send(raw)
                continue

            data = json.loads(raw)
            message_type = data.get("type", "")

            if message_type == "input_audio":
                await proxy.send(
                    {
                        "type": "input_audio_buffer.append",
                        "audio": data["audio_b64"],
                    }
                )
            elif message_type == "end_of_speech":
                await proxy.send({"type": "input_audio_buffer.commit"})
                await proxy.send({"type": "response.create"})
            elif message_type in ("user_text", "question"):
                text = (data.get("text") or data.get("question") or "").strip()
                if text:
                    await proxy.send(
                        {
                            "type": "conversation.item.create",
                            "item": {
                                "type": "message",
                                "role": "user",
                                "content": [{"type": "input_text", "text": text}],
                            },
                        }
                    )
                    await proxy.send({"type": "response.create"})
            elif message_type == "switch_partner":
                current_partner = data.get("partner", "both")
                new_brief = await context.build_realtime_brief(
                    case_id, partner=current_partner, topic=current_topic
                )
                current_instructions = compose_instructions(
                    voice_profile, new_brief, include_tools=is_openai
                )
                await proxy.send(
                    {
                        "type": "session.update",
                        "session": {
                            "type": "realtime",
                            "instructions": current_instructions,
                        },
                    }
                )
                await websocket.send_json(
                    {"type": "partner_switched", "partner_mode": current_partner}
                )
            elif message_type == "session.update":
                session = data.get("session", {})
                custom = session.get("instructions", "")
                if current_instructions not in custom:
                    session["instructions"] = f"{custom}\n\n{current_instructions}".strip()
                session.setdefault("audio", {}).setdefault("output", {})["voice"] = voice
                if is_openai:
                    session["tools"] = REALTIME_TOOLS
                data["session"] = session
                await proxy.send(data)
            else:
                await proxy.send(raw)

    async def forward_to_frontend() -> None:
        """Lane B: the proxy speaks, the household listens."""
        while True:
            message = await proxy.receive()

            # Only the tool calls need to be understood; everything else is
            # audio and is relayed untouched.
            if "function_call_arguments.done" not in message:
                await websocket.send_text(message)
                continue

            event = json.loads(message)
            if event.get("type") != "response.function_call_arguments.done":
                await websocket.send_text(message)
                continue

            call_id = event.get("call_id")
            if not call_id:
                await websocket.send_text(message)
                continue

            arguments = json.loads(event.get("arguments") or "{}")
            part = arguments.get("part", "financial-health")
            section = arguments.get("section", "score")
            sub_section = arguments.get("sub_section")
            label = f"{part}.{section}" + (f".{sub_section}" if sub_section else "")
            logger.info("The mentor asked for %s", label)

            await websocket.send_json({"type": "tool_call", "section": label})

            try:
                data = await context.get_section(
                    case_id,
                    part,
                    section,
                    sub_section,
                    compact_for_llm=True,
                )
                output = as_json(data)
            except Exception as exc:  # noqa: BLE001
                output = json.dumps({"error": str(exc)}, ensure_ascii=False)

            await proxy.send(
                {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": output,
                    },
                }
            )
            await proxy.send({"type": "response.create"})

    import asyncio

    tasks = [
        asyncio.create_task(forward_to_proxy()),
        asyncio.create_task(forward_to_frontend()),
    ]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in tasks:
            task.cancel()
        await proxy.close()
