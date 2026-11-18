"""The normalised view of a financial plan.

:class:`PlanDigest` is the only thing the AI layer ever sees.  It is built
from the raw MCP payloads (or from the offline case files) and is deliberately
bounded in size so a generation call always fits in the model's context.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class SourceRef:
    """A pointer back to the plan data a recommendation came from."""

    part: str
    section: str | None = None
    json_path: str | None = None
    quote: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "part": self.part,
            "section": self.section,
            "json_path": self.json_path,
            "quote": self.quote,
        }


@dataclass(frozen=True)
class Fact:
    """A figure the plan itself marks as quotable."""

    key: str
    value: Any = None
    unit: str | None = None
    label: str | None = None
    period: str | None = None


@dataclass(frozen=True)
class Concern:
    """An objective concern from the persona (O1, O2, ...)."""

    code: str
    title: str
    severity: str | None = None


@dataclass(frozen=True)
class Tension:
    """A tension between two parts of the plan (T1, T2, ...)."""

    code: str
    title: str
    severity: str | None = None


@dataclass(frozen=True)
class MetricCandidate:
    """A measurable number that a financial milestone can be built on."""

    metric_key: str
    metric_type: str
    value: Decimal
    unit: str
    label: str
    currency: str | None = None
    source_ref: SourceRef = field(default_factory=lambda: SourceRef(part="financial-health"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_key": self.metric_key,
            "metric_type": self.metric_type,
            "value": str(self.value),
            "unit": self.unit,
            "currency": self.currency,
            "label": self.label,
            "source_ref": self.source_ref.to_dict(),
        }


@dataclass
class PlanDigest:
    """Everything the milestone generator needs to know about a case."""

    case_id: str
    household_name: str | None = None
    language: str = "en"
    plan_date: date | None = None
    data_source: str = "mcp"
    score: dict[str, Any] | None = None
    facts: list[Fact] = field(default_factory=list)
    fact_rules: list[str] = field(default_factory=list)
    narratives: dict[str, str] = field(default_factory=dict)
    goals: dict[str, Any] = field(default_factory=dict)
    profile: dict[str, Any] = field(default_factory=dict)
    concerns: list[Concern] = field(default_factory=list)
    tensions: list[Tension] = field(default_factory=list)
    persona_sections: dict[str, str] = field(default_factory=dict)
    metrics: list[MetricCandidate] = field(default_factory=list)
    source_refs: list[SourceRef] = field(default_factory=list)
    #: Text blocks actually handed to the model, keyed by plan path.
    sections: dict[str, str] = field(default_factory=dict)
    #: Sections that did not fit in the context budget.
    omitted_sections: list[str] = field(default_factory=list)

    @property
    def fingerprint(self) -> str:
        """Content hash of the digest.

        Two digests with the same fingerprint describe the same plan, which
        is how the synchronisation detects that nothing changed.
        """
        hasher = hashlib.sha256()
        for key in sorted(self.sections):
            hasher.update(key.encode("utf-8"))
            hasher.update(b"\x00")
            hasher.update(self.sections[key].encode("utf-8"))
            hasher.update(b"\x00")
        for metric in sorted(self.metrics, key=lambda m: m.metric_key):
            hasher.update(metric.metric_key.encode("utf-8"))
            hasher.update(str(metric.value).encode("utf-8"))
        return hasher.hexdigest()

    def to_prompt_payload(self) -> dict[str, Any]:
        """The JSON payload handed to the model."""
        return {
            "case_id": self.case_id,
            "household_name": self.household_name,
            "language": self.language,
            "plan_date": self.plan_date.isoformat() if self.plan_date else None,
            "score": self.score,
            "facts": [
                {
                    "key": fact.key,
                    "value": fact.value,
                    "unit": fact.unit,
                    "label": fact.label,
                    "period": fact.period,
                }
                for fact in self.facts
            ],
            "fact_rules": self.fact_rules,
            "concerns": [
                {"code": c.code, "title": c.title, "severity": c.severity}
                for c in self.concerns
            ],
            "tensions": [
                {"code": t.code, "title": t.title, "severity": t.severity}
                for t in self.tensions
            ],
            "metrics": [metric.to_dict() for metric in self.metrics],
            "sections": self.sections,
            "omitted_sections": self.omitted_sections,
        }

    def to_json(self) -> str:
        """Canonical JSON of the prompt payload."""
        return json.dumps(self.to_prompt_payload(), ensure_ascii=False, sort_keys=True)

    def metric_by_key(self, metric_key: str) -> MetricCandidate | None:
        for metric in self.metrics:
            if metric.metric_key == metric_key:
                return metric
        return None

    def available_paths(self) -> set[str]:
        """The json paths the model is allowed to cite.

        Every block of plan data that reached the model contributes its own
        path plus the paths of everything inside it, so a citation like
        ``financial-health.key_metrics.debtManagement.listOfDebts`` is
        accepted while an invented path is not.
        """
        paths: set[str] = set()
        for key, text in self.sections.items():
            paths.add(key)
            tail = key.rsplit(".", 1)[-1]
            for relative in _json_paths(text):
                paths.add(f"{key}.{relative}")
                # The block name and its first key are often the same word
                # ("...facts" holding a "facts" key); both spellings are
                # accepted so the citation matches what the model read.
                if relative.startswith(f"{tail}."):
                    paths.add(f"{key}.{relative[len(tail) + 1 :]}")
        for ref in self.source_refs:
            if ref.json_path:
                paths.add(ref.json_path)
        return paths

    def path_is_known(self, json_path: str) -> bool:
        """Whether a citation points at something the model actually saw."""
        if json_path in self.available_paths():
            return True
        return any(
            known.endswith(f".{json_path}") for known in self.available_paths()
        )

    def available_source_refs(self) -> set[tuple[str, str | None, str | None]]:
        """The (part, section, json_path) triples the model is allowed to cite."""
        refs: set[tuple[str, str | None, str | None]] = set()
        for key in self.sections:
            part, _, path = key.partition(".")
            refs.add((part, None, path or None))
        for ref in self.source_refs:
            if ref.json_path is not None:
                refs.add((ref.part, ref.section, ref.json_path))
        return refs


def _json_paths(text: str, prefix: str = "") -> list[str]:
    """Every dotted path inside a JSON document (as text)."""
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return []
    paths: list[str] = []

    def walk(node: object, current: str) -> None:
        if isinstance(node, dict):
            for key in node:
                child = f"{current}.{key}" if current else str(key)
                paths.append(child)
                walk(node[key], child)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                child = f"{current}[{index}]"
                walk(item, child)

    walk(payload, prefix)
    return paths
