"""Payload compaction for the language model.

A tool answer has to fit in the context window of the conversation.  The raw
sections of a plan reach 57 KB, so they are compacted before they are handed
to the model: the projections are summarised and the bulky blocks are
reduced to the keys that matter.
"""

from __future__ import annotations

import json
from typing import Any

#: The most a tool answer may take.
MAX_TOOL_RESPONSE_CHARS = 5500

#: The years that are worth keeping in a projection table.
_KEY_YEARS = {2026, 2027, 2028, 2030, 2033, 2035, 2038, 2044, 2047}


def summarize_projections(projections: Any) -> Any:
    """Reduce the yearly projection table to the years that matter.

    The table holds one row per year of the plan (more than fifty).  Only the
    first years, the retirement horizon and the year the savings run out are
    worth the tokens.
    """
    if not isinstance(projections, dict):
        return projections

    years = projections.get("years") or projections.get("annual") or []
    if not years or not isinstance(years, list):
        raw = json.dumps(projections, ensure_ascii=False, separators=(",", ":"))
        if len(raw) <= MAX_TOOL_RESPONSE_CHARS:
            return projections
        return raw[:MAX_TOOL_RESPONSE_CHARS]

    key_indices = {0, 1, 2, 4, len(years) - 1}
    depletion_year: int | None = None
    for index, year in enumerate(years):
        if not isinstance(year, dict):
            continue
        number = year.get("year")
        if number in _KEY_YEARS:
            key_indices.add(index)
        assets = (
            year.get("investable_assets")
            or year.get("liquid_assets")
            or year.get("ending_savings")
        )
        if assets is not None and assets <= 0 and depletion_year is None:
            depletion_year = number
            key_indices.add(index)

    selected = [years[index] for index in sorted(key_indices) if 0 <= index < len(years)]
    return {
        "total_years_modeled": len(years),
        "first_depletion_year": depletion_year,
        "key_milestone_years": selected,
    }


def compact_payload(
    data: Any, section: str | None = None, sub_section: str | None = None
) -> Any:
    """Make sure a tool answer is small enough to be read.

    Nothing is cut in the middle: a block that does not fit is replaced by a
    summary of its keys, so the model can ask for the part it needs.
    """
    if isinstance(data, str):
        return data[:MAX_TOOL_RESPONSE_CHARS] if len(data) > MAX_TOOL_RESPONSE_CHARS else data

    if section == "projections":
        return summarize_projections(data)

    if isinstance(data, dict) and sub_section:
        if sub_section in data:
            data = {sub_section: data[sub_section]}
        else:
            lowered = sub_section.lower()
            matched = {key: value for key, value in data.items() if key.lower() == lowered}
            if matched:
                data = matched
            else:
                return {
                    "_hint": (
                        f"La sub-sección '{sub_section}' no existe. "
                        f"Elige una de: {list(data.keys())}"
                    )
                }

    serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if len(serialized) <= MAX_TOOL_RESPONSE_CHARS:
        return data

    if isinstance(data, dict):
        summary: dict[str, Any] = {
            "_notice": (
                "Sección resumida para ahorrar tokens. "
                "Pide `sub_section` para ampliar una clave."
            ),
            "available_sub_sections": list(data.keys()),
        }
        for key, value in data.items():
            encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            if len(encoded) <= 900:
                summary[key] = value
            elif isinstance(value, dict):
                preview = {
                    sub_key: sub_value
                    for sub_key, sub_value in list(value.items())[:10]
                    if isinstance(sub_value, (int, float, str, bool))
                    and len(str(sub_value)) < 160
                }
                if preview:
                    summary[key] = preview
        return summary

    return serialized[:MAX_TOOL_RESPONSE_CHARS]
