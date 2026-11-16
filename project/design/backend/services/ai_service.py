"""
services/ai_service.py
----------------------
Servicio de inteligencia artificial para endpoints clásicos (POST):
- Define los esquemas de herramientas (tools) para llamar a `get_case`.
- Ejecuta el ciclo de consulta a gpt-5-mini con razonamiento acotado y extracción de datos.
- Sintetiza texto a voz mediante la API de ElevenLabs (eleven-flash-v2.5).
"""

import json
from typing import Any, Dict, List, Tuple
from config import llm_client
from mcp_client import get_section

GET_CASE_PARAM_SCHEMA = {
    "type": "object",
    "properties": {
        "part": {
            "type": "string",
            "enum": ["financial-health", "investment-analysis", "persona"],
            "description": "Archivo del caso a consultar.",
        },
        "section": {
            "type": "string",
            "enum": [
                "score",
                "goals",
                "profile",
                "narrative",
                "projections",
                "key_metrics",
                "positions",
                "analysis",
                "D0",
                "D1",
                "D2",
                "D3",
                "D4",
                "D5",
                "D6",
                "Transition alerts",
                "Objective concerns",
                "Tensions",
            ],
            "description": (
                "Sección específica: 'positions' (cartera/ETFs), 'projections' (proyección año a año), "
                "'profile' (ingresos, gastos, cuentas, deudas, seguros), 'goals', 'key_metrics', "
                "'Objective concerns' o 'Tensions'."
            ),
        },
        "sub_section": {
            "type": "string",
            "description": (
                "Opcional para traer solo un sub-bloque ligero de 'profile' ('incomes', 'expenses', "
                "'accounts', 'liabilities', 'insurance') o de 'key_metrics' ('debtManagement', "
                "'protection', 'cashflowStatement', 'retirementAndOtherGoals', 'portfolioAnalysis', 'taxDragAnalysis')."
            ),
        },
    },
    "required": ["part", "section"],
}

CHAT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_case",
            "description": "Extrae únicamente una sección o sub-sección específica del expediente del cliente.",
            "parameters": GET_CASE_PARAM_SCHEMA,
        },
    }
]

REALTIME_TOOLS = [
    {
        "type": "function",
        "name": "get_case",
        "description": (
            "Úsala SOLO si el cliente pregunta por un detalle específico que no aparece en el "
            "brief inicial (ej. tickers exactos de ETFs en 'positions', proyección de un año específico "
            "en 'projections', o impuestos de inversión en 'taxDragAnalysis')."
        ),
        "parameters": GET_CASE_PARAM_SCHEMA,
    }
]


async def synthesize_elevenlabs_speech(text: str, voice_profile: Dict[str, str]) -> bytes:
    """Genera audio MP3 con ElevenLabs."""
    try:
        audio_resp = await llm_client.audio.speech.create(
            model="eleven-flash-v2.5",
            voice=voice_profile["voice_id"],
            input=text,
        )
        return audio_resp.content
    except Exception:
        audio_resp = await llm_client.audio.speech.create(
            model="eleven-flash-v2.5",
            voice=voice_profile["fallback_voice"],
            input=text,
        )
        return audio_resp.content


async def ask_llm_with_tools(
    client_id: str,
    question: str,
    brief: str,
    voice_profile: Dict[str, str],
) -> Tuple[str, bool, List[str]]:
    """
    Ejecuta el ciclo de consulta a gpt-5-mini con soporte de tool calling (get_case).
    Devuelve (texto_respuesta, mcp_usado, claves_consultadas).
    """
    messages: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "Eres el asesor de Sherpas Wealth, pero NO hablas como un banco aburrido.\n"
                f"{voice_profile['tone_instructions']}\n\n"
                "REGLA DE ORO: PROHIBIDO recitar listas de cifras, porcentajes o decimales. "
                "Usa los datos de abajo como tu chuleta interna y tradúcelos al registro del cliente "
                "(con refranes, metáforas o lenguaje callejero/ejecutivo según toque) en máximo 2 o 3 frases vivas.\n\n"
                f"CHULETA INTERNA:\n{brief}"
            ),
        },
        {"role": "user", "content": question},
    ]

    response = await llm_client.chat.completions.create(
        model="gemini-3.5-flash-lite",
        messages=messages,
        tools=CHAT_TOOLS,
        tool_choice="auto",
    )

    mensaje_ia = response.choices[0].message
    claves_consultadas: List[str] = []
    mcp_usado = False

    if mensaje_ia.tool_calls:
        mcp_usado = True
        messages.append(mensaje_ia)
        for tool_call in mensaje_ia.tool_calls[:2]:
            args = json.loads(tool_call.function.arguments or "{}")
            part = args.get("part", "financial-health")
            section = args.get("section", "score")
            sub_section = args.get("sub_section")
            etiqueta = f"{part}.{section}" + (f".{sub_section}" if sub_section else "")
            claves_consultadas.append(etiqueta)

            datos = await get_section(client_id, part, section, sub_section=sub_section)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(datos, ensure_ascii=False) if not isinstance(datos, str) else datos,
                }
            )

        respuesta_final = await llm_client.chat.completions.create(
            model="gemini-3.5-flash-lite",
            messages=messages,
        )
        texto_ia = (respuesta_final.choices[0].message.content or "").strip()
    else:
        texto_ia = (mensaje_ia.content or "").strip()

    return texto_ia, mcp_usado, claves_consultadas


async def build_gamified_path(client_id: str) -> Dict[str, Any]:
    """
    Genera el camino gamificado (Path) real a partir de los `top_moves` del plan
    financiero del cliente, adaptando los hitos a su situación particular.
    """
    from models import PathSchema, Nivel

    score_data = await get_section(client_id, "financial-health", "score")
    if not isinstance(score_data, dict):
        score_data = {}

    published_score = score_data.get("published_score", 50)
    banda = score_data.get("band", "vulnerable")
    top_moves = score_data.get("top_moves") or []

    # Recompensas temáticas según el tipo de hito
    recompensas_por_defecto = [
        "Insignia de Escudo Protector",
        "Medalla de Crecimiento Sostenible",
        "Trofeo de Libertad Financiera",
        "Insignia de Tranquilidad Familiar",
    ]

    niveles: List[Nivel] = []

    if top_moves:
        for idx, move in enumerate(top_moves):
            nivel_num = idx + 1
            # El primer nivel es el paso activo inmediato; los demás quedan bloqueados
            estado = "en_progreso" if idx == 0 else "bloqueado"
            progreso = 35 if idx == 0 else 0

            score_before = move.get("score_before", published_score)
            score_after = move.get("score_after", score_before)
            impacto = max(0, score_after - score_before)
            recompensa = f"+{impacto} Puntos de Score" if impacto > 0 else recompensas_por_defecto[idx % len(recompensas_por_defecto)]

            niveles.append(
                Nivel(
                    nivel_id=nivel_num,
                    titulo=move.get("title", f"Hito Financiero {nivel_num}"),
                    descripcion=move.get("action", "Sigue las recomendaciones del asesor para este hito."),
                    estado=estado,
                    progreso_porcentaje=progreso,
                    esfuerzo=move.get("effort", "medium"),
                    score_impacto=impacto,
                    recompensa_desbloqueo=recompensa,
                )
            )
    else:
        # Fallback si no tiene top_moves cargados
        niveles = [
            Nivel(
                nivel_id=1,
                titulo="Revisión de Salud Financiera",
                descripcion="Completa la sesión de diagnóstico inicial con tu asesor Sherpas.",
                estado="en_progreso",
                progreso_porcentaje=50,
                esfuerzo="low",
                score_impacto=5,
                recompensa_desbloqueo="Insignia de Diagnóstico",
            )
        ]

    return PathSchema(
        client_id=client_id,
        score_actual=published_score,
        banda_salud=banda,
        total_niveles=len(niveles),
        niveles=niveles,
    )

