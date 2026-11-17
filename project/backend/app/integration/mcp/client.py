"""Thin wrapper around the Sherpas MCP server.

The wrapper exists to give the rest of the application a small, typed API and
to translate transport failures into the exceptions in
:mod:`app.integration.mcp.errors`.  It never invents data.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any

from mcp.shared.exceptions import MCPError as SdkMcpError

from app.integration.mcp.errors import (
    McpAuthError,
    McpCaseNotFoundError,
    McpEmptyResponseError,
    McpError,
    McpProtocolError,
    McpSectionNotFoundError,
    McpUnavailableError,
)
from app.logging_config import get_logger

logger = get_logger(__name__)

_DEFAULT_TIMEOUT_SECONDS = 30.0


class McpClient:
    """Calls tools on the Sherpas MCP server over streamable HTTP."""

    def __init__(
        self,
        url: str,
        token: str,
        *,
        timeout: float = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._url = url
        self._token = token
        self._timeout = timeout

    # -- transport -------------------------------------------------------

    def _require_credentials(self) -> None:
        if not self._url or not self._token:
            raise McpAuthError("MCP credentials are not configured")

    @asynccontextmanager
    async def _session(self):
        """Open an MCP session.

        It is a separate method so the tests can replace the transport.
        """
        from mcp import ClientSession
        from mcp.client.streamable_http import (
            create_mcp_http_client,
            streamable_http_client,
        )

        http_client = create_mcp_http_client(
            headers={"Authorization": f"Bearer {self._token}"},
        )
        async with streamable_http_client(self._url, http_client=http_client) as (
            read,
            write,
            *_rest,  # type: ignore[var-annotated]
        ), ClientSession(read, write) as session:
            yield session

    async def call_tools(
        self, name: str, arguments_list: list[dict[str, Any]]
    ) -> list[Any]:
        """Call the same tool several times over a single connection."""
        self._require_credentials()
        if not arguments_list:
            return []

        results: list[Any] = []
        try:
            async with self._session() as session:
                await session.initialize()
                for arguments in arguments_list:
                    results.append(await session.call_tool(name, arguments))
        except McpError:
            raise
        except BaseException as exc:  # noqa: BLE001 - ExceptionGroups included
            raise await _classify(exc, self) from exc
        return [_extract_payload(result) for result in results]

    async def probe_status(self) -> int | None:
        """The HTTP status of the endpoint, or ``None`` when it is unreachable.

        Used to tell an expired token from a server that is down.
        """
        try:
            import httpx2

            async with httpx2.AsyncClient(timeout=15.0) as probe:
                response = await probe.post(
                    self._url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-06-18",
                            "capabilities": {},
                            "clientInfo": {"name": "sherpas-milestones", "version": "1.0"},
                        },
                    },
                    headers={
                        "Authorization": f"Bearer {self._token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream",
                    },
                )
                return response.status_code
        except Exception:  # noqa: BLE001 - the probe must never raise
            return None

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call one tool."""
        results = await self.call_tools(name, [arguments])
        return results[0]

    async def list_tools(self) -> list[dict[str, Any]]:
        """The tools the server exposes, with their input schemas."""
        self._require_credentials()

        try:
            async with self._session() as session:
                await session.initialize()
                listing = await session.list_tools()
        except McpError:
            raise
        except BaseException as exc:  # noqa: BLE001
            raise await _classify(exc, self) from exc

        tools: list[dict[str, Any]] = []
        for tool in getattr(listing, "tools", []) or []:
            schema = getattr(tool, "inputSchema", None) or {}
            tools.append(
                {
                    "name": getattr(tool, "name", ""),
                    "description": getattr(tool, "description", "") or "",
                    "input_schema": schema,
                }
            )
        return tools


def _extract_payload(result: Any) -> Any:
    """Turn an MCP tool result into plain Python data."""
    if result is None:
        raise McpEmptyResponseError("The MCP returned an empty result")

    is_error = bool(getattr(result, "isError", False))
    content = getattr(result, "content", None) or []

    text: str | None = None
    for item in content:
        item_text = getattr(item, "text", None)
        if isinstance(item_text, str):
            text = item_text
            break

    if text is None:
        structured = getattr(result, "structuredContent", None)
        if structured is not None:
            return structured
        if is_error:
            raise McpProtocolError("The MCP reported a tool error")
        raise McpEmptyResponseError("The MCP returned no textual content")

    if is_error:
        raise _error_from_payload(text)

    stripped = text.strip()
    if not stripped:
        raise McpEmptyResponseError("The MCP returned an empty payload")
    if stripped[0] not in "[{":
        # Plain text (the persona part is Markdown).
        return text
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise McpProtocolError("The MCP returned a payload that is not valid JSON") from exc
    if isinstance(payload, dict) and "value" in payload:
        return payload["value"]
    return payload


def _error_from_payload(text: str) -> McpError:
    lowered = text.lower()
    if "not found" in lowered or "no such case" in lowered:
        return McpCaseNotFoundError(text[:300])
    if "unknown section" in lowered or "invalid section" in lowered:
        return McpSectionNotFoundError(text[:300])
    if "unauthor" in lowered or "token" in lowered or "forbidden" in lowered:
        return McpAuthError(text[:300])
    return McpProtocolError(text[:300])


async def _classify(exc: BaseException, client: McpClient) -> McpError:
    """Map a transport failure onto one of our typed errors."""
    chain: list[BaseException] = []
    pending: list[BaseException] = [exc]
    while pending:
        current = pending.pop(0)
        if current is None or current in chain:
            continue
        chain.append(current)
        # An ExceptionGroup keeps its causes in ``exceptions``.
        children = getattr(current, "exceptions", None)
        if isinstance(children, (list, tuple)):
            pending.extend(
                child
                for child in children
                if isinstance(child, BaseException) and child not in chain
            )
        cause = current.__cause__ or current.__context__
        if isinstance(cause, BaseException) and cause not in chain:
            pending.append(cause)

    for error in chain:
        if isinstance(error, SdkMcpError):
            # The SDK turns an HTTP error into a JSON-RPC error and loses the
            # status, so we ask the endpoint what happened.
            return await _classify_sdk_error(error, client)
        status = getattr(error, "status_code", None) or getattr(
            getattr(error, "response", None), "status_code", None
        )
        if status == 401 or status == 403:
            return McpAuthError("The MCP rejected our credentials")
        if status == 404:
            return McpCaseNotFoundError("The MCP does not know this case")
        if isinstance(status, int) and status >= 500:
            return McpUnavailableError(f"The MCP answered with status {status}")
        name = type(error).__name__
        if name in {"ConnectError", "ConnectTimeout", "ReadTimeout", "TimeoutException"}:
            return McpUnavailableError("The MCP could not be reached")
        if name in {"HTTPStatusError"}:
            response = getattr(error, "response", None)
            code = getattr(response, "status_code", None)
            if code == 401 or code == 403:
                return McpAuthError("The MCP rejected our credentials")
            if code == 404:
                return McpCaseNotFoundError("The MCP does not know this case")
            return McpUnavailableError("The MCP answered with an error status")
        text = str(error).lower()
        if "401" in text or "unauthorized" in text or "invalid_token" in text:
            return McpAuthError("The MCP rejected our credentials")

    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return McpUnavailableError("The MCP could not be reached")
    return McpProtocolError(f"Unexpected MCP failure: {type(exc).__name__}")


async def _classify_sdk_error(error: SdkMcpError, client: McpClient) -> McpError:
    """Turn the error of the SDK into one of ours.

    The SDK hides the HTTP status of an error response, so the endpoint is
    asked directly what happened.
    """
    status = await client.probe_status()
    if status in (401, 403):
        return McpAuthError("The MCP rejected our credentials")
    if status == 404:
        return McpCaseNotFoundError("The MCP does not know this case")
    if status is not None and status >= 500:
        return McpUnavailableError(f"The MCP answered with status {status}")
    if status is None:
        return McpUnavailableError("The MCP could not be reached")
    return McpProtocolError(
        f"The MCP answered with status {status}: {error.message}"[:200]
    )
