"""The identifiers of the households.

The prototype addressed the households by a short name (``weah``); the plan
stores them under their full slug (``timothy-melanie-weah``).  Both are
accepted everywhere, so the client can use whichever it already has.
"""

from __future__ import annotations

#: Every alias of a household and the official slug of the case.
CASE_ALIASES: dict[str, str] = {
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

#: The short identifier of each case.
SHORT_ID_MAP: dict[str, str] = {
    "timothy-melanie-weah": "weah",
    "michael-carter": "carter",
    "daniel-emily-johnson": "johnson",
    "samantha-lewis": "lewis",
}


def normalize_case_id(client_id: str) -> str:
    """The official slug of a case, from any of its aliases."""
    clean = (client_id or "").strip().lower()
    if clean in CASE_ALIASES:
        return CASE_ALIASES[clean]
    for alias, slug in CASE_ALIASES.items():
        if alias in clean:
            return slug
    return clean


def get_short_id(client_id: str) -> str:
    """The short identifier of a case."""
    slug = normalize_case_id(client_id)
    return SHORT_ID_MAP.get(slug, slug)
