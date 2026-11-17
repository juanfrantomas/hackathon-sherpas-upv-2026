"""Turn raw plan payloads into a bounded :class:`PlanDigest`.

The raw payloads are large (100–150 KB per part) and repetitive.  The digest
keeps the parts that actually drive a milestone: the persona (which carries
the prioritised concerns), the per-area narratives, the quotable facts and the
balances a financial milestone could be measured against.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app.integration.mcp.digest import (
    Concern,
    Fact,
    MetricCandidate,
    PlanDigest,
    SourceRef,
    Tension,
)

#: The narrative fields of ``financial-health`` grouped by plan section.
NARRATIVE_AREAS: dict[str, tuple[str, ...]] = {
    "summary": ("summary_main", "summary_recommendations"),
    "debt": ("debt_short_observations", "debt_what_to_look_into"),
    "savings": ("savings_short_observations", "savings_what_to_look_into"),
    "assets": ("assets_short_observations", "assets_what_to_look_into"),
    "retirement": ("retirement_short_observations", "retirement_what_to_look_into"),
    "protection": (
        "protection_intro",
        "protection_emergency_fund_short_observations",
        "protection_life_insurance_short_observations",
        "protection_umbrella_short_observations",
    ),
}

#: Narrative fields of ``investment-analysis`` worth keeping.
INVESTMENT_NARRATIVE_FIELDS = (
    "summary_main",
    "portfolio_today_priorities",
    "recommendations_main",
    "recommendations_scenarios",
)

#: Sections of the digest, in the order they are added to the prompt.
_PRIORITY_ORDER = (
    "persona",
    "financial-health.narrative.summary",
    "financial-health.narrative.debt",
    "financial-health.narrative.savings",
    "financial-health.narrative.assets",
    "financial-health.narrative.retirement",
    "financial-health.narrative.protection",
    "financial-health.key_metrics.facts",
    "financial-health.profile.liabilities",
    "financial-health.profile.accounts",
    "financial-health.score",
    "financial-health.goals",
    "financial-health.key_metrics.debtManagement",
    "financial-health.key_metrics.savingsAndExpenses",
    "financial-health.key_metrics.protection",
    "financial-health.profile.incomes",
    "financial-health.profile.expenses",
    "financial-health.profile.insurance",
    "investment-analysis.narrative",
)

_PERSONA_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
#: ``- **O1: Title (SEVERITY).**`` or ``- **O1 SEVERITY: Title.**``
_ITEM_RE = re.compile(r"^-\s*\*\*([OT])(\d+)(.*)$")
_SEVERITY_WORDS = (
    "CRITICAL",
    "SIGNIFICANT",
    "HIGH",
    "MEDIUM",
    "MODERATE",
    "MINOR",
    "LOW",
)
#: ``Title (SEVERITY)`` at the end of the bold part.
_TITLE_THEN_SEVERITY_RE = re.compile(r"^:\s*(.+?)\s*\(([A-Z]+)\)\s*\.?\s*$")
#: ``SEVERITY: Title`` at the start of the bold part.
_SEVERITY_THEN_TITLE_RE = re.compile(r"^\s+([A-Z]+)\s*:\s*(.+?)\s*\.?\s*$")

_SPANISH_MARKERS = (
    " de ", " la ", " el ", " que ", " para ", " con ", " su ", " los ", " las ",
    " una ", " del ", " por ", " es ", " familia ", " però ",
)
_ENGLISH_MARKERS = (
    " the ", " and ", " of ", " is ", " to ", " with ", " household ", " family ",
    " are ", " for ",
)


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", (value or "").lower()).strip("_")
    return cleaned or "item"


def _household_name(case_block: dict[str, Any]) -> str | None:
    """The name of the household, from the case block.

    ``household`` is a list of members; only the adults (client and
    co-client) are part of the household name.
    """
    members = case_block.get("household") or []
    names: list[str] = []
    for member in members:
        if isinstance(member, dict):
            if member.get("role") in {"client", "co-client"}:
                first = str(member.get("first_name") or "").strip()
                if first:
                    names.append(first)
        elif isinstance(member, str):
            names.append(member.strip())
    if not names:
        return None
    return " & ".join(names) if len(names) == 2 else ", ".join(names)


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
    if isinstance(value, str):
        text = value.replace(",", "").replace("$", "").strip()
        if text.endswith("%"):
            text = text[:-1]
        try:
            return Decimal(text)
        except (InvalidOperation, ValueError):
            return None
    return None


def parse_classification(markdown: str) -> dict[str, str]:
    """The psychological classification the persona closes with.

    The persona ends with a fenced block::

        ```classification
        D0: EMERGING
        D5: COLLABORATOR
        ...
        ```

    It tells how the household decides, which the voice profiles and the
    mentor use to adapt their register.
    """
    match = re.search(
        r"```classification\s*(.*?)```", markdown, flags=re.DOTALL | re.IGNORECASE
    )
    if not match:
        return {}
    classification: dict[str, str] = {}
    for line in match.group(1).splitlines():
        entry = re.match(r"^(D\d)\s*:\s*(.+?)\s*$", line.strip())
        if entry:
            classification[entry.group(1)] = entry.group(2).strip()
    return classification


def extract_persona_section(markdown: str, section: str | None) -> str:
    """One section of the persona, by its short name.

    ``D0`` to ``D6``, ``Transition alerts``, ``Objective concerns``,
    ``Tensions`` or ``classification``.  Asking for a section that does not
    exist returns the classification rather than the whole file, so the model
    never reads nine kilobytes of Markdown by accident.
    """
    if not section or section.lower() in ("all", "full"):
        return markdown

    wanted = section.strip()

    if wanted.lower() == "classification":
        match = re.search(
            r"```classification\s*(.*?)```", markdown, flags=re.DOTALL | re.IGNORECASE
        )
        if match:
            return match.group(1).strip()

    pattern = rf"(^##\s+{re.escape(wanted)}\b.*?)(?=^##\s+|```classification|\Z)"
    match = re.search(pattern, markdown, flags=re.DOTALL | re.MULTILINE | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    classification = parse_classification(markdown)
    if classification:
        return "\n".join(f"{key}: {value}" for key, value in classification.items())
    return markdown[:1500]


def detect_language(texts: list[str]) -> str:
    """Very small language heuristic; the persona and narratives are English or Spanish."""
    sample = " ".join(texts).lower()
    spanish = sum(sample.count(marker) for marker in _SPANISH_MARKERS)
    english = sum(sample.count(marker) for marker in _ENGLISH_MARKERS)
    return "es" if spanish > english else "en"


def _parse_severity_item(remainder: str) -> tuple[str, str | None]:
    """Split a persona bullet into title and severity.

    The persona uses three layouts and this function understands all of them::

        ``: Title (SEVERITY).``                 -> ("Title", "SEVERITY")
        ``SEVERITY: Title.``                    -> ("Title", "SEVERITY")
        ``(SEVERITY):`` followed by the title   -> ("Title", "SEVERITY")
    """
    bold, _, rest = remainder.partition("**")
    rest = rest.strip()

    # ``(SEVERITY):`` - the title follows the bold part.
    match = re.match(r"^\s*\(([A-Z]+)\)\s*:\s*$", bold)
    if match is not None and match.group(1) in _SEVERITY_WORDS and rest:
        return rest.strip(" ."), match.group(1)

    # ``: Title (SEVERITY).``
    match = _TITLE_THEN_SEVERITY_RE.match(bold)
    if match is not None and match.group(2) in _SEVERITY_WORDS:
        return match.group(1).strip(" ."), match.group(2)

    # ``SEVERITY: Title.``
    match = _SEVERITY_THEN_TITLE_RE.match(bold)
    if match is not None and match.group(1) in _SEVERITY_WORDS:
        return match.group(2).strip(" ."), match.group(1)

    # No severity: keep whatever is left as the title.
    cleaned = bold.lstrip(": ").rstrip("*").strip(" .")
    return cleaned, None


def parse_persona(markdown: str) -> tuple[dict[str, str], list[Concern], list[Tension]]:
    """Split the persona markdown into sections, concerns and tensions."""
    sections: dict[str, str] = {}
    matches = list(_PERSONA_SECTION_RE.finditer(markdown))
    for index, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        sections[heading] = markdown[start:end].strip()

    concerns: list[Concern] = []
    tensions: list[Tension] = []
    for line in markdown.splitlines():
        item_match = _ITEM_RE.match(line.strip())
        if not item_match:
            continue
        kind, number, remainder = item_match.groups()
        code = f"{kind}{number}"
        title, severity = _parse_severity_item(remainder)
        if not title:
            continue
        if kind == "O":
            concerns.append(Concern(code=code, title=title, severity=severity))
        else:
            tensions.append(Tension(code=code, title=title, severity=severity))

    return sections, concerns, tensions


def extract_facts(financial_health: dict[str, Any]) -> tuple[list[Fact], list[str]]:
    """The quotable figures and the rules that govern their use."""
    facts_block = financial_health.get("key_metrics", {}).get("facts", {}) or {}
    rules = [str(rule) for rule in facts_block.get("rules", [])]
    facts: list[Fact] = []
    for group, entries in facts_block.items():
        if group == "rules" or not isinstance(entries, dict):
            continue
        for name, fact in entries.items():
            if not isinstance(fact, dict):
                continue
            facts.append(
                Fact(
                    key=f"{group}.{name}",
                    value=fact.get("value"),
                    unit=fact.get("unit"),
                    label=fact.get("label"),
                    period=fact.get("period"),
                )
            )
    return facts, rules


def extract_metrics(
    financial_health: dict[str, Any], facts: list[Fact]
) -> list[MetricCandidate]:
    """Measurable numbers a financial milestone could be built on."""
    metrics: list[MetricCandidate] = []
    profile = financial_health.get("profile", {}) or {}

    for liability in profile.get("liabilities", []) or []:
        balance = _to_decimal(liability.get("balance"))
        if balance is None:
            continue
        name = str(liability.get("name") or "liability")
        metrics.append(
            MetricCandidate(
                metric_key=f"liability_{_slug(name)}",
                metric_type="balance",
                value=balance,
                unit="USD",
                label=f"Outstanding balance of {name}",
                currency="USD",
                source_ref=SourceRef(
                    part="financial-health",
                    section="profile",
                    json_path="profile.liabilities",
                ),
            )
        )

    for account in profile.get("accounts", []) or []:
        balance = _to_decimal(account.get("balance"))
        if balance is None:
            continue
        name = str(account.get("name") or "account")
        account_type = str(account.get("account_type") or "").lower()
        metric_type = (
            "savings"
            if any(word in account_type for word in ("checking", "savings", "cash"))
            else "balance"
        )
        metrics.append(
            MetricCandidate(
                metric_key=f"account_{_slug(name)}",
                metric_type=metric_type,
                value=balance,
                unit="USD",
                label=f"Balance of {name}",
                currency="USD",
                source_ref=SourceRef(
                    part="financial-health",
                    section="profile",
                    json_path="profile.accounts",
                ),
            )
        )

    for fact in facts:
        if not fact.unit or fact.unit != "USD":
            continue
        value = _to_decimal(fact.value)
        if value is None:
            continue
        metrics.append(
            MetricCandidate(
                metric_key=f"fact_{_slug(fact.key)}",
                metric_type="balance",
                value=value,
                unit="USD",
                label=fact.label or fact.key,
                currency="USD",
                source_ref=SourceRef(
                    part="financial-health",
                    section="key_metrics",
                    json_path=f"key_metrics.facts.{fact.key}",
                ),
            )
        )
    return metrics


def _slim_score(financial_health: dict[str, Any]) -> dict[str, Any]:
    score = financial_health.get("score", {}) or {}
    return {
        key: score.get(key)
        for key in ("published_score", "scale", "band", "message", "explainer")
        if key in score
    }


def _slim_facts(facts: list[Fact], rules: list[str]) -> dict[str, Any]:
    return {
        "rules": rules,
        "facts": {
            fact.key: {
                "value": fact.value,
                "unit": fact.unit,
                "label": fact.label,
                "period": fact.period,
            }
            for fact in facts
        },
    }


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def build_sections(
    *,
    financial_health: dict[str, Any],
    investment_analysis: dict[str, Any],
    persona: str,
    facts: list[Fact],
    fact_rules: list[str],
) -> dict[str, str]:
    """The individual blocks that may be sent to the model."""
    narrative = financial_health.get("narrative", {}) or {}
    profile = financial_health.get("profile", {}) or {}
    key_metrics = financial_health.get("key_metrics", {}) or {}

    sections: dict[str, str] = {"persona": persona}

    for area, fields in NARRATIVE_AREAS.items():
        chunk = {
            field: narrative[field]
            for field in fields
            if isinstance(narrative.get(field), str) and narrative.get(field)
        }
        if chunk:
            sections[f"financial-health.narrative.{area}"] = _dump(chunk)

    sections["financial-health.key_metrics.facts"] = _dump(_slim_facts(facts, fact_rules))

    for group in ("liabilities", "accounts", "incomes", "expenses", "insurance"):
        value = profile.get(group)
        if value:
            sections[f"financial-health.profile.{group}"] = _dump(value)

    score = _slim_score(financial_health)
    if score:
        sections["financial-health.score"] = _dump(score)

    goals = financial_health.get("goals")
    if goals:
        sections["financial-health.goals"] = _dump(goals)

    for group in ("debtManagement", "savingsAndExpenses", "protection"):
        value = key_metrics.get(group)
        if value:
            sections[f"financial-health.key_metrics.{group}"] = _dump(value)

    investment_narrative = investment_analysis.get("narrative", {}) or {}
    chunk = {
        field: investment_narrative[field]
        for field in INVESTMENT_NARRATIVE_FIELDS
        if isinstance(investment_narrative.get(field), str)
    }
    if chunk:
        sections["investment-analysis.narrative"] = _dump(chunk)

    return sections


def _split_oversized(text: str, limit: int) -> list[str]:
    """Split an oversized JSON block into its top-level keys."""
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(payload, dict):
        return []
    parts: list[str] = []
    for key in sorted(payload):
        candidate = _dump({key: payload[key]})
        if len(candidate) <= limit:
            parts.append(candidate)
    return parts


def apply_budget(
    sections: dict[str, str], *, max_chars: int
) -> tuple[dict[str, str], list[str]]:
    """Keep the highest priority blocks that fit in the context budget."""
    ordered = [key for key in _PRIORITY_ORDER if key in sections]
    ordered += [key for key in sections if key not in _PRIORITY_ORDER]

    kept: dict[str, str] = {}
    omitted: list[str] = []
    used = 0
    for key in ordered:
        text = sections[key]
        if used + len(text) <= max_chars:
            kept[key] = text
            used += len(text)
            continue
        # A single oversized block is split by its own keys instead of being cut.
        for part in _split_oversized(text, max_chars):
            if used + len(part) <= max_chars:
                kept[f"{key}#{len(kept)}"] = part
                used += len(part)
        omitted.append(key)
    return kept, omitted


def normalize_plan(
    case_id: str,
    *,
    financial_health: dict[str, Any],
    investment_analysis: dict[str, Any] | None = None,
    persona: str = "",
    data_source: str = "mcp",
    max_chars: int = 60_000,
    plan_date: date | None = None,
) -> PlanDigest:
    """Build the digest the generator works from."""
    investment_analysis = investment_analysis or {}
    facts, fact_rules = extract_facts(financial_health)
    persona_sections, concerns, tensions = parse_persona(persona)
    metrics = extract_metrics(financial_health, facts)

    sections = build_sections(
        financial_health=financial_health,
        investment_analysis=investment_analysis,
        persona=persona,
        facts=facts,
        fact_rules=fact_rules,
    )
    kept, omitted = apply_budget(sections, max_chars=max_chars)

    narratives: dict[str, str] = {}
    narrative_block = financial_health.get("narrative", {}) or {}
    for area, fields in NARRATIVE_AREAS.items():
        text = " ".join(
            str(narrative_block[field])
            for field in fields
            if isinstance(narrative_block.get(field), str) and narrative_block.get(field)
        ).strip()
        if text:
            narratives[area] = text

    source_refs: list[SourceRef] = [
        SourceRef(part="financial-health", section="narrative", json_path="narrative"),
        SourceRef(part="financial-health", section="key_metrics", json_path="key_metrics.facts"),
        SourceRef(part="persona", section="objective_concerns", json_path="persona.concerns"),
    ]
    source_refs.extend(metric.source_ref for metric in metrics)

    household = financial_health.get("case", {}) or {}
    household_name = _household_name(household)

    language = detect_language([persona, *narratives.values()])

    digest = PlanDigest(
        case_id=case_id,
        household_name=household_name,
        language=language,
        plan_date=plan_date,
        data_source=data_source,
        score=_slim_score(financial_health),
        facts=facts,
        fact_rules=fact_rules,
        narratives=narratives,
        goals=financial_health.get("goals", {}) or {},
        profile=financial_health.get("profile", {}) or {},
        concerns=concerns,
        tensions=tensions,
        persona_sections=persona_sections,
        metrics=metrics,
        source_refs=source_refs,
        sections=kept,
        omitted_sections=omitted,
    )
    return digest


def stable_case_fingerprint(payload: str) -> str:
    """Hash used by the offline source to detect changes."""
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
