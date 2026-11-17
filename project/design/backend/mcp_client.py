"""
mcp_client.py
-------------
Capa de acceso y extracción inteligente de datos de los clientes.
- Acepta IDs cortos ('weah', 'carter', 'johnson', 'lewis') o slugs completos.
- Prioriza la lectura local instantánea en `cases/` con caché en memoria por documento (_PART_CACHE)
  y fallback al servidor MCP remoto, reduciendo la latencia de arranque a < 5ms.
- Protege el presupuesto de tokens recortando y resumiendo secciones masivas (>6KB como key_metrics o projections)
  incluso cuando el LLM no especifica `sub_section`.
- Construye briefs ejecutivos ultraligeros con soporte para Modo Pareja (`partner`) y foco de hito (`topic`).
"""

import os
import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

load_dotenv()

MCP_URL = os.getenv("MCP_URL", "https://mcp-hackathon.sherpaswealth.com/mcp")
MCP_TOKEN = os.getenv("MCP_TOKEN")

# Ruta local a la carpeta cases/ del repositorio (instantáneo y sin caducidad)
REPO_CASES_DIR = Path(__file__).resolve().parents[3] / "cases"

# Mapa de alias cortos (usados en el frontend) -> slug oficial en cases/
CASE_ALIASES: Dict[str, str] = {
    "weah": "timothy-melanie-weah",
    "timothy": "timothy-melanie-weah",
    "melanie": "timothy-melanie-weah",
    "timothy-melanie-weah": "timothy-melanie-weah",
    "carter": "michael-carter",
    "michael": "michael-carter",
    "michael-carter": "michael-carter",
    "johnson": "daniel-emily-johnson",
    "daniel": "daniel-emily-johnson",
    "emily": "daniel-emily-johnson",
    "daniel-emily-johnson": "daniel-emily-johnson",
    "lewis": "samantha-lewis",
    "samantha": "samantha-lewis",
    "samantha-lewis": "samantha-lewis",
}

SHORT_ID_MAP: Dict[str, str] = {
    "timothy-melanie-weah": "weah",
    "michael-carter": "carter",
    "daniel-emily-johnson": "johnson",
    "samantha-lewis": "lewis",
}

# Cachés en memoria para evitar lecturas de disco o llamadas de red repetidas
_PART_CACHE: Dict[str, Any] = {}
_SECTION_CACHE: Dict[str, Any] = {}

MAX_TOOL_RESPONSE_CHARS = 5500


def normalize_case_id(client_id: str) -> str:
    """Normaliza cualquier alias ('weah', 'carter', etc.) al slug oficial de cases/."""
    clean = (client_id or "").strip().lower()
    if clean in CASE_ALIASES:
        return CASE_ALIASES[clean]
    for alias, full_slug in CASE_ALIASES.items():
        if alias in clean:
            return full_slug
    return clean or "timothy-melanie-weah"


def get_short_id(client_id: str) -> str:
    """Devuelve el ID corto ('weah', 'carter', 'johnson', 'lewis') para el frontend."""
    slug = normalize_case_id(client_id)
    return SHORT_ID_MAP.get(slug, slug)


def _extract_persona_section(markdown_text: str, section: Optional[str]) -> str:
    """
    Extrae únicamente una sección del archivo persona.md (ej. 'D0'..'D6',
    'Transition alerts', 'Objective concerns', 'Tensions', 'classification').
    """
    if not section or section.lower() in ("all", "full"):
        return markdown_text

    sec_clean = section.strip()

    # Bloque de clasificación compacto (~120 tokens)
    if sec_clean.lower() == "classification":
        match = re.search(r"```classification\s*(.*?)```", markdown_text, flags=re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # Buscar encabezado ## que coincida con D0..D6 o con el nombre de la sección
    pattern = rf"(^##\s+{re.escape(sec_clean)}\b.*?)(?=^##\s+|```classification|\Z)"
    match = re.search(pattern, markdown_text, flags=re.DOTALL | re.MULTILINE | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Si no coincide con ninguna sección, devolver solo clasificación para no filtrar 9KB
    match_cls = re.search(r"```classification\s*(.*?)```", markdown_text, flags=re.DOTALL | re.IGNORECASE)
    return match_cls.group(1).strip() if match_cls else markdown_text[:1500]


async def _load_full_part(case_id: str, part: str) -> Any:
    """
    Carga y cachea en memoria una parte completa ('financial-health', 'investment-analysis' o 'persona').
    Lee primero de disco local (cases/) en <1ms; si no existe en disco, consulta el servidor MCP.
    """
    case_id = normalize_case_id(case_id)
    part_key = f"{case_id}::{part}"
    if part_key in _PART_CACHE:
        return _PART_CACHE[part_key]

    case_dir = REPO_CASES_DIR / case_id
    if case_dir.exists():
        if part == "persona":
            persona_path = case_dir / "persona.md"
            if persona_path.exists():
                content = persona_path.read_text(encoding="utf-8")
                _PART_CACHE[part_key] = content
                return content
        else:
            json_path = case_dir / f"{part}.json"
            if json_path.exists():
                content = json.loads(json_path.read_text(encoding="utf-8"))
                _PART_CACHE[part_key] = content
                return content

    # Fallback a MCP remoto si no estuviera en disco local
    if MCP_URL and MCP_TOKEN:
        try:
            http = create_mcp_http_client(headers={"Authorization": f"Bearer {MCP_TOKEN}"})
            async with streamable_http_client(MCP_URL, http_client=http) as (read, write, *_):
                async with ClientSession(read, write) as mcp:
                    await mcp.initialize()
                    r = await mcp.call_tool("get_case", {"caseId": case_id, "part": part})
                    texto_respuesta = r.content[0].text
                    if part == "persona":
                        try:
                            parsed = json.loads(texto_respuesta)
                            content = parsed.get("value", texto_respuesta) if isinstance(parsed, dict) else texto_respuesta
                        except json.JSONDecodeError:
                            content = texto_respuesta
                    else:
                        parsed = json.loads(texto_respuesta)
                        content = parsed.get("value", parsed) if isinstance(parsed, dict) else parsed
                    _PART_CACHE[part_key] = content
                    return content
        except BaseException as e:
            print(f"⚠️ MCP aviso ({case_id}/{part}): {e}")

    raise FileNotFoundError(f"No se pudo cargar '{part}' para el caso '{case_id}'")


def _summarize_projections(proj_data: Any) -> Any:
    """
    Compacta la tabla anual de proyecciones (~10.5 KB) a los hitos clave (inicio, 2027, 2030,
    jubilación, posible agotamiento de ahorros y final del plan) ahorrando ~85% de tokens.
    """
    if not isinstance(proj_data, dict):
        return proj_data

    years: List[Dict[str, Any]] = proj_data.get("years") or proj_data.get("annual") or []
    if not years or not isinstance(years, list):
        raw = json.dumps(proj_data, ensure_ascii=False, separators=(",", ":"))
        return proj_data if len(raw) <= MAX_TOOL_RESPONSE_CHARS else raw[:MAX_TOOL_RESPONSE_CHARS]

    key_Indices = {0, 1, 2, 4, len(years) - 1}
    depletion_year = None
    for idx, yr in enumerate(years):
        if isinstance(yr, dict):
            yr_num = yr.get("year")
            if yr_num in (2026, 2027, 2028, 2030, 2033, 2035, 2038, 2044, 2047):
                key_Indices.add(idx)
            # Detectar primer año donde activos líquidos o ahorros caen a <= 0
            inv = yr.get("investable_assets") or yr.get("liquid_assets") or yr.get("ending_savings")
            if inv is not None and inv <= 0 and depletion_year is None:
                depletion_year = yr_num
                key_Indices.add(idx)

    selected = [years[i] for i in sorted(key_Indices) if 0 <= i < len(years)]
    return {
        "total_years_modeled": len(years),
        "first_depletion_year": depletion_year,
        "key_milestone_years": selected,
    }


def _compact_large_payload(data: Any, section: Optional[str], sub_section: Optional[str]) -> Any:
    """
    Garantiza que ninguna llamada a `get_case` devuelva 40KB-57KB de JSON crudo al LLM,
    incluso cuando el modelo olvida pasar `sub_section`.
    """
    if isinstance(data, str):
        return data[:MAX_TOOL_RESPONSE_CHARS] if len(data) > MAX_TOOL_RESPONSE_CHARS else data

    if section == "projections":
        return _summarize_projections(data)

    if isinstance(data, dict) and sub_section:
        if sub_section in data:
            data = {sub_section: data[sub_section]}
        else:
            sub_lower = sub_section.lower()
            matched = {k: v for k, v in data.items() if k.lower() == sub_lower}
            if matched:
                data = matched
            else:
                return {
                    "_hint": f"Sub-sección '{sub_section}' no existe. Elige una de: {list(data.keys())}",
                }

    serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if len(serialized) <= MAX_TOOL_RESPONSE_CHARS:
        return data

    # Si es un diccionario masivo (como key_metrics de 57KB sin sub_section),
    # devolvemos un resumen compacto por clave sin saturar los tokens del modelo.
    if isinstance(data, dict):
        compact_summary: Dict[str, Any] = {
            "_notice": "Sección resumida para ahorrar tokens. Pide `sub_section` para ampliar una clave.",
            "available_sub_sections": list(data.keys()),
        }
        for k, v in data.items():
            v_str = json.dumps(v, ensure_ascii=False, separators=(",", ":"))
            if len(v_str) <= 900:
                compact_summary[k] = v
            elif isinstance(v, dict):
                # Incluir solo valores escalares o resúmenes cortos del primer nivel
                scalar_preview = {
                    sk: sv
                    for sk, sv in list(v.items())[:10]
                    if isinstance(sv, (int, float, str, bool)) and len(str(sv)) < 160
                }
                if scalar_preview:
                    compact_summary[k] = scalar_preview
        return compact_summary

    return serialized[:MAX_TOOL_RESPONSE_CHARS]


async def get_section(
    case_id: str,
    part: str,
    section: Optional[str] = None,
    sub_section: Optional[str] = None,
    compact_for_llm: bool = False,
) -> Any:
    """
    Obtiene una sección específica de un caso en microsegundos desde la caché en memoria.
    Si `compact_for_llm=True` (usado en Tool Calling), recorta secciones gigantes para ahorrar tokens.
    """
    case_id = normalize_case_id(case_id)
    cache_key = f"{case_id}::{part}::{section or '*'}::{sub_section or '*'}::{int(compact_for_llm)}"
    if cache_key in _SECTION_CACHE:
        return _SECTION_CACHE[cache_key]

    full_doc = await _load_full_part(case_id, part)

    if part == "persona":
        raw_section = _extract_persona_section(full_doc, section)
    else:
        if section and isinstance(full_doc, dict):
            if section in full_doc:
                raw_section = full_doc[section]
            else:
                raw_section = {"_error": f"Sección '{section}' no encontrada. Disponibles: {list(full_doc.keys())}"}
        else:
            raw_section = full_doc

    if compact_for_llm or sub_section:
        result = _compact_large_payload(raw_section, section, sub_section)
    else:
        result = raw_section

    _SECTION_CACHE[cache_key] = result
    return result


async def get_compact_client_context(case_id: str) -> Dict[str, Any]:
    """
    Extrae en <1ms el contexto ligero del hogar:
    - Datos básicos de los miembros y si es una pareja (`is_couple`)
    - Score publicado y banda
    - Clasificación psicológica (`classification`)
    """
    case_id = normalize_case_id(case_id)
    case_info = await get_section(case_id, "financial-health", "case")
    score_info = await get_section(case_id, "financial-health", "score")
    classification = await get_section(case_id, "persona", "classification")

    household_list = (case_info.get("household") if isinstance(case_info, dict) else []) or []
    adults = [p for p in household_list if p.get("role") in ("client", "co-client")]
    children = [p for p in household_list if p.get("role") == "child"]

    return {
        "case_id": case_id,
        "short_id": get_short_id(case_id),
        "household": case_info,
        "adults": adults,
        "children": children,
        "is_couple": len(adults) >= 2,
        "score_summary": {
            "published_score": score_info.get("published_score") if isinstance(score_info, dict) else None,
            "band": score_info.get("band") if isinstance(score_info, dict) else None,
        },
        "classification": classification,
    }


async def get_couple_dynamics(case_id: str) -> Dict[str, Any]:
    """
    Extrae la radiografía de pareja (Modo Pareja - criterio 'Personal: for each of them'):
    Perfiles de riesgo individuales (Growth vs Moderate), reparto de roles (D5),
    tensiones financieras entre ambos (Tensions) y la propuesta de consenso.
    """
    case_id = normalize_case_id(case_id)
    ctx = await get_compact_client_context(case_id)
    adults = ctx["adults"]
    is_couple = ctx["is_couple"]

    d4_risk = await get_section(case_id, "persona", "D4")
    d5_style = await get_section(case_id, "persona", "D5")
    tensions = await get_section(case_id, "persona", "Tensions")

    members_summary = []
    for a in adults:
        name = a.get("first_name", "")
        risk = a.get("risk_profile", "Moderate")
        ret_age = a.get("retirement_age", 62)
        focus = (
            "Crecimiento, rentabilidad y coste de oportunidad fiscal/inversor"
            if risk.lower() == "growth"
            else "Seguridad familiar, colchón de liquidez y protección de los hijos"
        )
        members_summary.append(
            {
                "key": name.lower(),
                "name": name,
                "role": a.get("role"),
                "age": a.get("age"),
                "retirement_age": ret_age,
                "risk_profile": risk,
                "personal_focus": focus,
            }
        )

    if case_id == "timothy-melanie-weah":
        consensus_bridge = (
            "Timothy (perfil Growth) busca que el dinero rinda y no perder un 18% en la tarjeta, "
            "mientras que Melanie (perfil Moderate) prioriza la seguridad de Liam y Josh con un gran colchón de liquidez. "
            "El punto de encuentro: usar solo una parte del efectivo excedente ($60k sobre la reserva) para liquidar "
            "la tarjeta al 18% y cubrir el seguro de vida mantiene intacto el fondo de emergencia de Melanie y logra "
            "el retorno garantizado que busca Timothy, subiendo su Score de 60 a 73."
        )
    elif case_id == "daniel-emily-johnson":
        consensus_bridge = (
            "Emily (perfil Moderate) gestiona todo el ahorro anual ($26k/año hacia bróker y 529 de los niños), "
            "mientras que Daniel (perfil Growth) figura en la tarjeta al 24.9% y ninguno aporta hoy al 401(k). "
            "El punto de encuentro: redirigir temporalmente parte del flujo hacia liquidar la tarjeta al 24.9% y "
            "asegurar la vida de ambos protege a Oliver y Sophia (prioridad de Emily) y libera flujo para activar "
            "el ahorro fiscal del 401(k) (prioridad de Daniel), subiendo el Score de 52 a 60."
        )
    else:
        single_name = adults[0].get("first_name", "Cliente") if adults else "Cliente"
        consensus_bridge = (
            f"Plan individual para {single_name}: alinear la liquidez de corto plazo con el perfil Growth de largo plazo."
        )

    return {
        "case_id": case_id,
        "is_couple": is_couple,
        "members": members_summary,
        "decision_style": d5_style,
        "risk_alignment": d4_risk,
        "tensions": tensions,
        "consensus_bridge": consensus_bridge,
    }


def _build_partner_instruction(couple_data: Dict[str, Any], partner_param: Optional[str]) -> str:
    """
    Construye la directriz de personalización ('Modo Pareja') según con quién hable el asesor:
    - Nombre de uno de los miembros (ej. 'timothy', 'melanie', 'daniel', 'emily')
    - 'both' / 'couple' / 'auto' (mediación activa entre ambos perfiles cuando es pareja)
    """
    members = couple_data.get("members", [])
    if not couple_data.get("is_couple") or len(members) < 2:
        if members:
            m = members[0]
            return (
                f"INTERLOCUTOR: Hablas directamente con {m['name']} ({m['age']} años, perfil de riesgo {m['risk_profile']})."
            )
        return ""

    m1, m2 = members[0], members[1]
    p_clean = (partner_param or "auto").strip().lower()

    # Si eligieron hablar específicamente como el miembro 1 o 2
    for m, other in ((m1, m2), (m2, m1)):
        if p_clean in (m["key"], m["role"]):
            return (
                f"MODO PAREJA (HABLANDO AHORA CON {m['name'].upper()}):\n"
                f"- Estás hablando con {m['name']} ({m['age']} años, perfil {m['risk_profile']}), cuya prioridad es: {m['personal_focus']}.\n"
                f"- Su pareja es {other['name']} ({other['age']} años, perfil {other['risk_profile']}), que prioriza: {other['personal_focus']}.\n"
                f"- Adapta tus argumentos al enfoque de {m['name']}, pero explícale cómo la recomendación también deja tranquila a su pareja {other['name']} para que tomen la decisión juntos.\n"
                f"- PUENTE DE CONSENSO DE LA PAREJA: {couple_data['consensus_bridge']}"
            )

    # Por defecto en parejas ('both' / 'couple' / 'auto'): Mediador de pareja dirigéndose a ambos
    return (
        f"MODO PAREJA ACTIVO ({m1['name']} & {m2['name']}):\n"
        f"- Este plan pertenece a DOS personas con visiones distintas: {m1['name']} es perfil {m1['risk_profile']} ({m1['personal_focus']}) "
        f"y {m2['name']} es perfil {m2['risk_profile']} ({m2['personal_focus']}).\n"
        f"- Dirígete a ambos por sus nombres ({m1['name']} y {m2['name']}) de forma natural. Cuando expliques un paso, "
        f"muestra en una frase por qué le encaja al lado práctico/rentable de {m1['name']} y por qué protege la tranquilidad que busca {m2['name']}.\n"
        f"- PUENTE DE CONSENSO: {couple_data['consensus_bridge']}"
    )


async def build_realtime_brief(
    case_id: str,
    partner: Optional[str] = None,
    topic: Optional[str] = None,
) -> str:
    """
    Construye un brief ultraligero (~450-550 tokens) para la sesión de IA:
    Incluye datos del hogar, Score y saltos de puntos por hito, brechas clave (D3),
    Modo Pareja (si aplica) y el tema concreto (`topic`) desde el que entra el usuario.
    """
    case_id = normalize_case_id(case_id)
    fh_case = await get_section(case_id, "financial-health", "case")
    fh_score = await get_section(case_id, "financial-health", "score")
    fh_narrative = await get_section(case_id, "financial-health", "narrative")
    d3_gaps = await get_section(case_id, "persona", "D3")
    alerts = await get_section(case_id, "persona", "Transition alerts")
    couple_data = await get_couple_dynamics(case_id)

    household_list = (fh_case.get("household") if isinstance(fh_case, dict) else []) or []
    people = ", ".join(
        f"{p.get('first_name')} ({p.get('role')}, {p.get('age')} años)" for p in household_list
    )
    city = fh_case.get("city", "") if isinstance(fh_case, dict) else ""
    state = fh_case.get("state", "") if isinstance(fh_case, dict) else ""

    score_val = fh_score.get("published_score") if isinstance(fh_score, dict) else "N/A"
    raw_band = (fh_score.get("band") if isinstance(fh_score, dict) else "") or ""
    friendly_bands = {
        "critical": "Punto de Impulso (Alto potencial de mejora rápida)",
        "vulnerable": "En Evolución (Base sólida por coordinar)",
        "stable": "Equilibrado",
        "strong": "Base Patrimonial Fuerte",
    }
    score_band = friendly_bands.get(raw_band.lower(), raw_band)
    top_moves = (fh_score.get("top_moves") if isinstance(fh_score, dict) else []) or []
    combined_moves = (fh_score.get("combined_moves") if isinstance(fh_score, dict) else []) or []

    moves_txt = "; ".join(
        f"{m.get('title')}: {m.get('action')} (Score {m.get('score_before')}->{m.get('score_after')})"
        for m in top_moves
    )
    if combined_moves:
        best_combo = max(combined_moves, key=lambda c: c.get("score_after", 0))
        moves_txt += f" | COMBINADOS ({' + '.join(best_combo.get('moves', []))}): sube el Score hasta {best_combo.get('score_after')}."

    recs = ""
    if isinstance(fh_narrative, dict):
        recs = fh_narrative.get("summary_recommendations") or ""

    # Omitir alertas si dice "None detected" para ahorrar tokens en cada turno
    clean_alerts = ""
    if isinstance(alerts, str) and "none detected" not in alerts.lower():
        clean_alerts = alerts

    partner_block = _build_partner_instruction(couple_data, partner)
    topic_block = (
        f"TEMA ACTIVO SELECCIONADO POR EL CLIENTE EN LA APP: '{topic}'. "
        "Céntrate directamente en resolver y guiar sobre este punto."
        if topic
        else ""
    )

    emotional_guides = {
        "michael-carter": (
            "GUÍA EMOCIONAL (CERO MIEDO): Michael tiene una puntuación inicial de 26, pero PROHIBIDO decirle que está en 'estado crítico' o que 'gasta más de lo que ingresa'. "
            "Felicítalo primero porque gana $180,000, no tiene deudas malas y ahorra $43,000 al año. Explícale con suavidad y optimismo que solo necesita acompasar el ritmo entre su futura casa de 2027 y su retiro a los 58 años para dar un salto directo de 26 a 62 puntos."
        ),
        "daniel-emily-johnson": (
            "GUÍA EMOCIONAL (TEMAS SENSIBLES CON TACTO): Al hablar del seguro de vida ($1.6M recomendados frente a $250k actuales), PROHIBIDO mencionar muerte, fallecimiento o tragedias. "
            "Exprésalo con calidez como 'poner una red de tranquilidad debajo del hogar para que los sueños y la universidad de Oliver y Sophia estén siempre garantizados pase lo que pase'."
        ),
        "timothy-melanie-weah": (
            "GUÍA EMOCIONAL (TRANQUILIDAD EN PAREJA): Valora el gran colchón de $150,800 que han logrado reunir. Al hablar de la tarjeta y del seguro de vida para Liam y Josh, "
            "hazlo desde la serenidad familiar y el alivio de quitar pequeños frenos sin tocar su seguridad."
        ),
        "samantha-lewis": (
            "GUÍA EMOCIONAL (HORIZONTE DE VIDA): Al explicar la proyección de liquidez a los 73 años, NUNCA uses frases alarmistas como 'te quedarás sin dinero en la vejez'. "
            "Enfócalo de forma constructiva como 'darle ventaja fiscal a tu gran ahorro anual para que tu liquidez acompañe tu ritmo de vida con total holgura hasta los 90 años'."
        ),
    }
    emotional_block = emotional_guides.get(case_id, "")

    partes = [
        f"HOGAR: {people} ({city}, {state}). PUNTUACIÓN INICIAL: {score_val}/100 ({score_band}).",
        emotional_block,
        partner_block,
        topic_block,
        moves_txt and f"PASOS QUE IMPULSAN SU PLAN:\n{moves_txt}",
        f"CONTEXTO INTERNO DEL EXPEDIENTE (TRADUCIR CON SUAVIDAD Y OPTIMISMO):\n{d3_gaps}",
        clean_alerts and f"HITO CERCANO EN CALENDARIO:\n{clean_alerts}",
        recs and f"RECOMENDACIÓN CLAVE DE SHERPAS:\n{recs}",
    ]
    return "\n\n".join(p for p in partes if p)
