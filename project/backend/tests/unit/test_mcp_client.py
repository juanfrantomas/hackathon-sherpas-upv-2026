"""The MCP client and the case sources.

The transport is replaced by a fake session, so the suite never talks to the
real server (and the personal MCP token only lasts 72 hours anyway).
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import pytest

from app.integration.mcp.case_source import (
    AutoCaseSource,
    LocalCaseSource,
    McpCaseSource,
)
from app.integration.mcp.client import McpClient
from app.integration.mcp.errors import (
    McpAuthError,
    McpCaseNotFoundError,
    McpEmptyResponseError,
    McpProtocolError,
    McpUnavailableError,
)


@dataclass
class FakeContent:
    text: str


@dataclass
class FakeResult:
    content: list[FakeContent]
    isError: bool = False


@dataclass
class FakeTool:
    name: str
    description: str = ""
    inputSchema: dict = field(default_factory=dict)


@dataclass
class FakeListing:
    tools: list[FakeTool]


class FakeSession:
    """A stand-in for the MCP session."""

    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[tuple[str, dict]] = []
        self.initialized = False

    async def initialize(self) -> None:
        self.initialized = True

    async def call_tool(self, name: str, arguments: dict) -> Any:
        self.calls.append((name, arguments))
        response = self.responses.get(name, {})
        if callable(response):
            return response(arguments)
        return response

    async def list_tools(self) -> Any:
        return FakeListing(
            tools=[
                FakeTool(
                    name="get_case",
                    description="Fetch a case",
                    inputSchema={"type": "object", "properties": {}},
                ),
                FakeTool(name="list_cases", description="List the cases"),
            ]
        )


class FakeMcpClient(McpClient):
    """A client whose transport is a fake session."""

    def __init__(self, responses: dict[str, Any] | None = None, **kwargs: Any) -> None:
        super().__init__("https://example.invalid/mcp", "token", **kwargs)
        self.session = FakeSession(responses)

    @asynccontextmanager
    async def _session(self):
        yield self.session


def _json_result(payload: Any) -> FakeResult:
    return FakeResult([FakeContent(json.dumps(payload))])


def test_the_client_unwraps_the_value_envelope():
    client = FakeMcpClient({"get_case": _json_result({"value": {"caseId": "abc"}})})
    result = asyncio.run(client.call_tool("get_case", {"caseId": "abc"}))
    assert result == {"caseId": "abc"}


def test_the_client_keeps_plain_text():
    client = FakeMcpClient({"get_case": FakeResult([FakeContent("# Persona")])})
    result = asyncio.run(client.call_tool("get_case", {"caseId": "abc"}))
    assert result == "# Persona"


def test_the_client_reports_the_tools():
    client = FakeMcpClient()
    tools = asyncio.run(client.list_tools())
    assert {tool["name"] for tool in tools} == {"get_case", "list_cases"}
    assert tools[0]["input_schema"]["type"] == "object"


def test_the_client_refuses_to_work_without_credentials():
    client = McpClient("", "")
    with pytest.raises(McpAuthError):
        asyncio.run(client.call_tool("get_case", {}))


def test_an_empty_answer_is_reported():
    client = FakeMcpClient({"get_case": FakeResult([FakeContent("")], isError=False)})
    with pytest.raises(McpEmptyResponseError):
        asyncio.run(client.call_tool("get_case", {}))


def test_a_payload_that_is_not_json_is_reported():
    client = FakeMcpClient({"get_case": FakeResult([FakeContent("{not json")], isError=True)})
    with pytest.raises(McpProtocolError):
        asyncio.run(client.call_tool("get_case", {}))


def test_a_missing_case_is_reported():
    client = FakeMcpClient(
        {"get_case": FakeResult([FakeContent("case not found")], isError=True)}
    )
    with pytest.raises(McpCaseNotFoundError):
        asyncio.run(client.call_tool("get_case", {}))


def test_a_connection_failure_is_reported():
    class BrokenClient(FakeMcpClient):
        @asynccontextmanager
        async def _session(self):
            raise ConnectionError("no route to host")
            yield  # pragma: no cover

    with pytest.raises(McpUnavailableError):
        asyncio.run(BrokenClient().call_tool("get_case", {}))


def test_the_error_of_the_sdk_is_classified_with_the_http_status():
    from mcp.shared.exceptions import MCPError as SdkMcpError

    class SdkErrorClient(FakeMcpClient):
        @asynccontextmanager
        async def _session(self):
            raise SdkMcpError(code=-32603, message="Server returned an error response")
            yield  # pragma: no cover

    client = SdkErrorClient()

    async def probe() -> int:
        return 401

    client.probe_status = probe  # type: ignore[method-assign]
    with pytest.raises(McpAuthError):
        asyncio.run(client.call_tool("get_case", {}))


def test_an_unreachable_endpoint_is_reported_as_unavailable():
    from mcp.shared.exceptions import MCPError as SdkMcpError

    class SdkErrorClient(FakeMcpClient):
        @asynccontextmanager
        async def _session(self):
            raise SdkMcpError(code=-32603, message="Server returned an error response")
            yield  # pragma: no cover

    client = SdkErrorClient()

    async def probe() -> int | None:
        return None

    client.probe_status = probe  # type: ignore[method-assign]
    with pytest.raises(McpUnavailableError):
        asyncio.run(client.call_tool("get_case", {}))


def test_the_case_source_reads_the_sections_it_needs(cases_dir):
    client = FakeMcpClient(
        {
            "get_case": lambda arguments: _json_result(
                {"value": {"section": arguments.get("section")}}
            )
        }
    )
    source = McpCaseSource(client)
    digest = asyncio.run(source.get_digest("timothy-melanie-weah"))
    assert digest.sections
    requested = [arguments.get("section") for name, arguments in client.session.calls]
    assert "narrative" in requested
    assert "profile" in requested


def test_the_case_source_lists_the_cases(cases_dir):
    client = FakeMcpClient({"list_cases": _json_result({"value": [{"caseId": "abc"}]})})
    source = McpCaseSource(client)
    cases = asyncio.run(source.list_cases())
    assert cases == [{"caseId": "abc"}]


def test_the_case_source_caches_the_tools():
    client = FakeMcpClient()
    source = McpCaseSource(client)
    asyncio.run(source.list_tools())
    asyncio.run(source.list_tools())
    assert client.session.initialized


def test_the_local_source_reads_the_case_files(cases_dir):
    source = LocalCaseSource(cases_dir)
    digest = asyncio.run(source.get_digest("timothy-melanie-weah"))
    assert digest.sections
    assert digest.metrics
    assert digest.fingerprint


def test_the_local_source_reports_an_unknown_case(cases_dir):
    source = LocalCaseSource(cases_dir)
    with pytest.raises(McpCaseNotFoundError):
        asyncio.run(source.get_digest("not-a-case"))


def test_the_local_source_lists_the_cases(cases_dir):
    source = LocalCaseSource(cases_dir)
    cases = asyncio.run(source.list_cases())
    assert len(cases) == 4
    assert all(case["caseId"] for case in cases)


def test_the_auto_source_falls_back_to_the_offline_files(cases_dir):
    class BrokenClient(FakeMcpClient):
        @asynccontextmanager
        async def _session(self):
            raise ConnectionError("no route to host")
            yield  # pragma: no cover

    source = AutoCaseSource(
        McpCaseSource(BrokenClient()), LocalCaseSource(cases_dir)
    )
    digest = asyncio.run(source.get_digest("timothy-melanie-weah"))
    assert digest.data_source == "local"
    assert source.last_error == "MCP_UNAVAILABLE"
    assert source.data_source == "local"


def test_the_auto_source_uses_the_mcp_when_it_works(cases_dir):
    client = FakeMcpClient(
        {
            "get_case": lambda arguments: _json_result(
                {"value": {"section": arguments.get("section")}}
            )
        }
    )
    source = AutoCaseSource(McpCaseSource(client), LocalCaseSource(cases_dir))
    digest = asyncio.run(source.get_digest("timothy-melanie-weah"))
    assert digest.data_source == "mcp"
    assert source.data_source == "mcp"
