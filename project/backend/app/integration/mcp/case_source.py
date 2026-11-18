"""Access to the Sherpas case data.

Two interchangeable sources implement :class:`CaseSource`:

``McpCaseSource``
    Talks to the Sherpas MCP server over streamable HTTP.
``LocalCaseSource``
    Reads the very same payloads from the offline ``cases/`` directory.

``AutoCaseSource`` prefers the MCP and falls back to the local files when the
MCP is unreachable (a personal MCP token only lasts 72 hours).  Neither
source ever invents financial data: when neither can serve a case the caller
gets a ``FINANCIAL_PLAN_NOT_FOUND`` error.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from app.domain.cases import normalize_case_id
from app.integration.mcp.client import McpClient
from app.integration.mcp.digest import PlanDigest
from app.integration.mcp.errors import (
    McpAuthError,
    McpCaseNotFoundError,
    McpEmptyResponseError,
    McpError,
    McpProtocolError,
    McpSectionNotFoundError,
    McpUnavailableError,
)
from app.integration.mcp.normalizer import normalize_plan
from app.logging_config import get_logger

logger = get_logger(__name__)

#: Top level sections of ``financial-health`` the milestone generator needs.
FINANCIAL_HEALTH_SECTIONS = ("case", "score", "goals", "profile", "narrative", "key_metrics")
#: Top level sections of ``investment-analysis`` the milestone generator needs.
INVESTMENT_ANALYSIS_SECTIONS = ("case", "narrative", "positions")

_CACHE_TTL_SECONDS = 3600.0


@runtime_checkable
class CaseSource(Protocol):
    """Everything the application needs from a case provider."""

    data_source: str

    async def list_cases(self) -> list[dict[str, Any]]: ...

    async def get_case_overview(self, case_id: str) -> dict[str, Any]: ...

    async def get_part(self, case_id: str, part: str) -> Any: ...

    async def get_section(self, case_id: str, part: str, section: str) -> Any: ...

    async def get_digest(self, case_id: str) -> PlanDigest: ...


class _TTLCache:
    """Small in-process cache with a time to live."""

    def __init__(self, ttl: float = _CACHE_TTL_SECONDS) -> None:
        self._ttl = ttl
        self._entries: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.monotonic():
            self._entries.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._entries[key] = (time.monotonic() + self._ttl, value)

    def clear(self) -> None:
        self._entries.clear()


class McpCaseSource:
    """Reads case data from the Sherpas MCP server."""

    data_source = "mcp"

    def __init__(self, client: McpClient, *, max_chars: int = 60_000) -> None:
        self._client = client
        self._max_chars = max_chars
        self._cache = _TTLCache()
        self._tool_lock = asyncio.Lock()
        self._tools: list[dict[str, Any]] | None = None

    # -- discovery ------------------------------------------------------

    async def list_tools(self) -> list[dict[str, Any]]:
        """The tools the server exposes (cached for an hour)."""
        if self._tools is not None:
            return self._tools
        async with self._tool_lock:
            if self._tools is None:
                self._tools = await self._client.list_tools()
        return self._tools

    async def list_cases(self) -> list[dict[str, Any]]:
        """The cases the server knows about."""
        cached = self._cache.get("cases")
        if cached is not None:
            return cached
        try:
            tools = await self.list_tools()
        except McpError:
            tools = []
        names = {tool.get("name") for tool in tools}
        if "list_cases" not in names:
            raise McpSectionNotFoundError("list_cases is not available on this server")
        payload = await self._client.call_tool("list_cases", {})
        cases = _extract_cases(payload)
        self._cache.set("cases", cases)
        return cases

    async def get_case_overview(self, case_id: str) -> dict[str, Any]:
        """The case overview: available parts and section sizes."""
        case_id = normalize_case_id(case_id)
        cached = self._cache.get(f"overview:{case_id}")
        if cached is not None:
            return cached
        payload = await self._client.call_tool("get_case", {"caseId": case_id})
        overview = payload if isinstance(payload, dict) else {"value": payload}
        self._cache.set(f"overview:{case_id}", overview)
        return overview

    async def get_part(self, case_id: str, part: str) -> Any:
        """A whole part of the case."""
        case_id = normalize_case_id(case_id)
        cached = self._cache.get(f"part:{case_id}:{part}")
        if cached is not None:
            return cached
        payload = await self._client.call_tool(
            "get_case", {"caseId": case_id, "part": part}
        )
        self._cache.set(f"part:{case_id}:{part}", payload)
        return payload

    async def get_section(self, case_id: str, part: str, section: str) -> Any:
        """One section of a part."""
        case_id = normalize_case_id(case_id)
        cache_key = f"section:{case_id}:{part}:{section}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        payload = await self._client.call_tool(
            "get_case", {"caseId": case_id, "part": part, "section": section}
        )
        self._cache.set(cache_key, payload)
        return payload

    async def _collect_part(
        self, case_id: str, part: str, sections: tuple[str, ...]
    ) -> dict[str, Any]:
        """Fetch the sections we need and merge them into one payload.

        The whole part in one call would also drag in ``projections`` and the
        bulk of ``key_metrics``, which the generator never uses.
        """
        calls = [
            {"caseId": case_id, "part": part, "section": section}
            for section in sections
        ]
        try:
            payloads = await self._client.call_tools("get_case", calls)
        except McpError as exc:
            logger.info("Section fetch failed for %s/%s, falling back to the whole part", part, exc)
            whole = await self.get_part(case_id, part)
            return whole if isinstance(whole, dict) else {}

        merged: dict[str, Any] = {}
        for section, payload in zip(sections, payloads, strict=False):
            value = payload
            if isinstance(payload, dict) and "value" in payload:
                value = payload["value"]
            if isinstance(value, dict):
                merged[section] = value
        return merged

    async def get_digest(self, case_id: str) -> PlanDigest:
        """Build the digest from the live case."""
        case_id = normalize_case_id(case_id)
        financial_health = await self._collect_part(
            case_id, "financial-health", FINANCIAL_HEALTH_SECTIONS
        )
        investment_analysis = await self._collect_part(
            case_id, "investment-analysis", INVESTMENT_ANALYSIS_SECTIONS
        )
        persona = await self.get_part(case_id, "persona")
        if isinstance(persona, dict):
            persona = persona.get("value") or persona.get("narrative") or ""
        if not isinstance(persona, str):
            persona = str(persona or "")
        return normalize_plan(
            case_id,
            financial_health=financial_health,
            investment_analysis=investment_analysis,
            persona=persona,
            data_source=self.data_source,
            max_chars=self._max_chars,
        )


class LocalCaseSource:
    """Reads the same payloads from the offline ``cases/`` directory."""

    data_source = "local"

    def __init__(self, cases_dir: Path, *, max_chars: int = 60_000) -> None:
        self._cases_dir = Path(cases_dir)
        self._max_chars = max_chars
        self._cache = _TTLCache()

    def _case_dir(self, case_id: str) -> Path:
        return self._cases_dir / normalize_case_id(case_id)

    def _has_case(self, case_id: str) -> bool:
        return (self._case_dir(case_id) / "financial-health.json").is_file()

    async def list_cases(self) -> list[dict[str, Any]]:
        cases: list[dict[str, Any]] = []
        if not self._cases_dir.is_dir():
            return cases
        for entry in sorted(self._cases_dir.iterdir()):
            if not entry.is_dir():
                continue
            overview = self._read_json(entry / "financial-health.json")
            if not overview:
                continue
            cases.append(
                {
                    "caseId": entry.name,
                    "household": (overview.get("case") or {}).get("household"),
                    "city": (overview.get("case") or {}).get("city"),
                    "state": (overview.get("case") or {}).get("state"),
                    "score": (overview.get("score") or {}).get("published_score"),
                    "parts": ["financial-health", "investment-analysis", "persona"],
                }
            )
        return cases

    def _read_json(self, path: Path) -> dict[str, Any]:
        if not path.is_file():
            return {}
        try:
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read %s: %s", path.name, exc)
            return {}

    async def get_case_overview(self, case_id: str) -> dict[str, Any]:
        payload = self._read_json(self._case_dir(case_id) / "financial-health.json")
        if not payload:
            raise McpCaseNotFoundError(f"Case {case_id} is not available offline")
        return {
            "caseId": case_id,
            "parts": {
                name: {"sections": list(payload.keys())}
                for name in ("financial-health",)
            },
        }

    async def get_part(self, case_id: str, part: str) -> Any:
        case_id = normalize_case_id(case_id)
        if part == "persona":
            path = self._case_dir(case_id) / "persona.md"
            if path.is_file():
                return path.read_text(encoding="utf-8")
            return ""
        payload = self._read_json(self._case_dir(case_id) / f"{part}.json")
        if not payload:
            raise McpCaseNotFoundError(f"Part {part} of case {case_id} is not available")
        return payload

    async def get_section(self, case_id: str, part: str, section: str) -> Any:
        payload = await self.get_part(case_id, part)
        if isinstance(payload, dict):
            return payload.get(section)
        return None

    async def get_digest(self, case_id: str) -> PlanDigest:
        case_id = normalize_case_id(case_id)
        if not self._has_case(case_id):
            raise McpCaseNotFoundError(f"Case {case_id} is not available offline")
        financial_health = self._read_json(
            self._case_dir(case_id) / "financial-health.json"
        )
        investment_analysis = self._read_json(
            self._case_dir(case_id) / "investment-analysis.json"
        )
        persona_path = self._case_dir(case_id) / "persona.md"
        persona = persona_path.read_text(encoding="utf-8") if persona_path.is_file() else ""
        return normalize_plan(
            case_id,
            financial_health=financial_health,
            investment_analysis=investment_analysis,
            persona=persona,
            data_source=self.data_source,
            max_chars=self._max_chars,
        )


class AutoCaseSource:
    """Prefers the MCP, falls back to the offline files."""

    def __init__(self, mcp_source: McpCaseSource, local_source: LocalCaseSource) -> None:
        self._mcp = mcp_source
        self._local = local_source
        self.data_source = "mcp"
        self.last_error: str | None = None

    async def list_cases(self) -> list[dict[str, Any]]:
        try:
            return await self._mcp.list_cases()
        except McpError as exc:
            self.last_error = exc.code
            return await self._local.list_cases()

    async def get_case_overview(self, case_id: str) -> dict[str, Any]:
        try:
            overview = await self._mcp.get_case_overview(case_id)
            self.data_source = "mcp"
            return overview
        except McpError as exc:
            self.last_error = exc.code
            self.data_source = "local"
            return await self._local.get_case_overview(case_id)

    async def get_part(self, case_id: str, part: str) -> Any:
        try:
            payload = await self._mcp.get_part(case_id, part)
            self.data_source = "mcp"
            return payload
        except McpError as exc:
            self.last_error = exc.code
            self.data_source = "local"
            return await self._local.get_part(case_id, part)

    async def get_section(self, case_id: str, part: str, section: str) -> Any:
        try:
            payload = await self._mcp.get_section(case_id, part, section)
            self.data_source = "mcp"
            return payload
        except McpError as exc:
            self.last_error = exc.code
            self.data_source = "local"
            return await self._local.get_section(case_id, part, section)

    async def get_digest(self, case_id: str) -> PlanDigest:
        try:
            digest = await self._mcp.get_digest(case_id)
            self.data_source = "mcp"
            return digest
        except McpError as exc:
            self.last_error = exc.code
            logger.warning("MCP unavailable (%s), falling back to the offline case files", exc.code)
            self.data_source = "local"
            return await self._local.get_digest(case_id)


def _extract_cases(payload: Any) -> list[dict[str, Any]]:
    """Normalise whatever ``list_cases`` answered into a list of dicts."""
    if isinstance(payload, dict):
        for key in ("cases", "value", "items", "data"):
            if key in payload:
                payload = payload[key]
                break
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


__all__ = [
    "AutoCaseSource",
    "CaseSource",
    "LocalCaseSource",
    "McpCaseSource",
    "McpAuthError",
    "McpCaseNotFoundError",
    "McpEmptyResponseError",
    "McpProtocolError",
    "McpUnavailableError",
]
