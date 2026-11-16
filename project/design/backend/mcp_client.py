"""
mcp_client.py
-------------
Capa de acceso y extracción inteligente de datos de los clientes.
- Consulta el servidor MCP de Sherpas o los archivos JSON/Markdown locales de cases/.
- Implementa una caché en memoria (_SECTION_CACHE) para evitar latencias de red.
- Permite la extracción granular por sección y sub-sección (para reducir el uso de tokens).
- Construye briefs ejecutivos ligeros (~850 tokens) para inicializar las sesiones de Realtime.
"""

import os
import re
import json
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

load_dotenv()

MCP_URL = os.getenv("MCP_URL", "https://mcp-hackathon.sherpaswealth.com/mcp")
MCP_TOKEN = os.getenv("MCP_TOKEN")

# Ruta local a la carpeta cases/ del repositorio (fallback instantáneo y sin caducidad)
REPO_CASES_DIR = Path(__file__).resolve().parents[3] / "cases"

# Caché en memoria para no repetir llamadas de red al MCP en la misma sesión
_SECTION_CACHE: Dict[str, Any] = {}


def _extract_persona_section(markdown_text: str, section: Optional[str]) -> str:
    """
    Extrae únicamente una sección del archivo persona.md (ej. 'D0'..'D6',
    'Transition alerts', 'Objective concerns', 'Tensions', 'classification').
    """
    if not section or section.lower() in ("all", "full"):
        return markdown_text

    sec_clean = section.strip()

    # Si piden el bloque de clasificación compacto (~150 tokens)
    if sec_clean.lower() == "classification":
        match = re.search(r"```classification\s*(.*?)```", markdown_text, flags=re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # Buscar encabezado ## que coincida con D0..D6 o con el nombre de la sección
    pattern = rf"(^##\s+{re.escape(sec_clean)}\b.*?)(?=^##\s+|\Z)"
    match = re.search(pattern, markdown_text, flags=re.DOTALL | re.MULTILINE | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return markdown_text


def _read_local_case(case_id: str, part: str, section: Optional[str] = None) -> Any:
    """
    Lee directamente desde cases/<case_id>/ en disco si el MCP falla o no hay token.
    """
    case_dir = REPO_CASES_DIR / case_id
    if not case_dir.exists():
        raise FileNotFoundError(f"No existe el caso '{case_id}' en {REPO_CASES_DIR}")

    if part == "persona":
        persona_path = case_dir / "persona.md"
        text = persona_path.read_text(encoding="utf-8")
        return _extract_persona_section(text, section)

    json_filename = f"{part}.json"
    json_path = case_dir / json_filename
    if not json_path.exists():
        raise FileNotFoundError(f"No existe el archivo '{json_filename}' para '{case_id}'")

    data = json.loads(json_path.read_text(encoding="utf-8"))
    if section:
        if section in data:
            return data[section]
        raise KeyError(f"La sección '{section}' no existe en '{part}' ({list(data.keys())})")
    return data


def _filter_sub_section(data: Any, sub_section: Optional[str]) -> Any:
    """
    Si la sección es un diccionario grande (como key_metrics o profile),
    extrae únicamente la sub-clave solicitada para ahorrar miles de tokens.
    """
    if not sub_section or not isinstance(data, dict):
        return data

    # Búsqueda exacta o insensible a mayúsculas/minúsculas
    if sub_section in data:
        return {sub_section: data[sub_section]}

    sub_lower = sub_section.lower()
    for k, v in data.items():
        if k.lower() == sub_lower:
            return {k: v}

    # Si no coincide, devolvemos las claves disponibles o el diccionario original si es pequeño
    serialized = json.dumps(data)
    if len(serialized) > 8000:
        # Recortamos para nunca saturar el contexto con 40KB de key_metrics
        return {
            "_notice": f"Sub-sección '{sub_section}' no encontrada. Claves disponibles: {list(data.keys())}",
            "facts": data.get("facts", {}),
        }
    return data


async def get_section(
    case_id: str,
    part: str,
    section: Optional[str] = None,
    sub_section: Optional[str] = None,
) -> Any:
    """
    Obtiene una sección específica de un caso desde el MCP de Sherpas (con caché en memoria)
    y fallback automático a los JSON/Markdown reales de la carpeta cases/.
    """
    cache_key = f"{case_id}::{part}::{section or '*'}::{sub_section or '*'}"
    if cache_key in _SECTION_CACHE:
        return _SECTION_CACHE[cache_key]

    base_cache_key = f"{case_id}::{part}::{section or '*'}::*"
    raw_result = _SECTION_CACHE.get(base_cache_key)

    if raw_result is None:
        # 1. Intentar por MCP si hay credenciales configuradas
        if MCP_URL and MCP_TOKEN and section != "classification":
            try:
                http = create_mcp_http_client(headers={"Authorization": f"Bearer {MCP_TOKEN}"})
                async with streamable_http_client(MCP_URL, http_client=http) as (read, write, *_):
                    async with ClientSession(read, write) as mcp:
                        await mcp.initialize()
                        argumentos = {"caseId": case_id, "part": part}
                        if section:
                            argumentos["section"] = section

                        r = await mcp.call_tool("get_case", argumentos)
                        texto_respuesta = r.content[0].text

                        if part == "persona":
                            # El MCP puede devolver texto plano o un JSON con {"value": "..."}
                            try:
                                parsed = json.loads(texto_respuesta)
                                raw_result = parsed.get("value", texto_respuesta) if isinstance(parsed, dict) else texto_respuesta
                            except json.JSONDecodeError:
                                raw_result = texto_respuesta
                            raw_result = _extract_persona_section(raw_result, section)
                        else:
                            parsed = json.loads(texto_respuesta)
                            raw_result = parsed.get("value", parsed) if isinstance(parsed, dict) else parsed
            except BaseException as e:
                print(f"⚠️ MCP aviso ({case_id}/{part}/{section}): usando lectura local rápida ({e})")

        # 2. Fallback instantáneo a los archivos reales de cases/
        if raw_result is None:
            raw_result = _read_local_case(case_id, part, section)

        _SECTION_CACHE[base_cache_key] = raw_result

    final_result = _filter_sub_section(raw_result, sub_section)
    _SECTION_CACHE[cache_key] = final_result
    return final_result


async def get_compact_client_context(case_id: str) -> Dict[str, Any]:
    """
    Extrae un contexto ultraligero (~350 tokens en total) al iniciar la sesión:
    - Datos básicos de household (case)
    - Puntuación general (score.published_score y band)
    - Clasificación psicológica D0..D6, alertas y preocupaciones (persona classification)
    """
    case_info = await get_section(case_id, "financial-health", "case")
    score_info = await get_section(case_id, "financial-health", "score")
    classification = await get_section(case_id, "persona", "classification")
    d5_style = await get_section(case_id, "persona", "D5")
    d6_anchor = await get_section(case_id, "persona", "D6")

    return {
        "household": case_info,
        "score_summary": {
            "published_score": score_info.get("published_score") if isinstance(score_info, dict) else None,
            "band": score_info.get("band") if isinstance(score_info, dict) else None,
        },
        "classification": classification,
        "decision_style": d5_style,
        "motivational_anchor": d6_anchor,
    }


async def build_realtime_brief(case_id: str) -> str:
    """
    Construye un brief ultraligero (~850 tokens) para la sesión Realtime WebSocket:
    Combina los datos clave del hogar, el score, el resumen ejecutivo de brechas (D3 de persona.md)
    y las recomendaciones principales del plan sin cargar los 90KB de JSON.
    """
    fh_case = await get_section(case_id, "financial-health", "case")
    fh_score = await get_section(case_id, "financial-health", "score")
    fh_narrative = await get_section(case_id, "financial-health", "narrative")
    d3_gaps = await get_section(case_id, "persona", "D3")
    alerts = await get_section(case_id, "persona", "Transition alerts")

    household_list = (fh_case.get("household") if isinstance(fh_case, dict) else []) or []
    people = ", ".join(
        f"{p.get('first_name')} ({p.get('role')}, {p.get('age')} años)" for p in household_list
    )
    city = fh_case.get("city", "") if isinstance(fh_case, dict) else ""
    state = fh_case.get("state", "") if isinstance(fh_case, dict) else ""

    score_val = fh_score.get("published_score") if isinstance(fh_score, dict) else "N/A"
    score_band = fh_score.get("band") if isinstance(fh_score, dict) else ""

    recs = ""
    if isinstance(fh_narrative, dict):
        recs = fh_narrative.get("summary_recommendations") or fh_narrative.get("summary_main") or ""

    partes = [
        f"FAMILIA: {people} ({city}, {state}).",
        f"FINANCIAL HEALTH SCORE: {score_val}/100 (banda: {score_band}).",
        f"RESUMEN DE CIFRAS Y BRECHAS CLAVE (D3):\n{d3_gaps}",
        alerts and f"ALERTAS DE TRANSICIÓN:\n{alerts}",
        recs and f"RECOMENDACIONES PRINCIPALES DE SHERPAS:\n{recs}",
    ]
    return "\n\n".join(p for p in partes if p)

