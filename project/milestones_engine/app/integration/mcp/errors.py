"""Typed errors raised by the MCP integration.

The module never fabricates financial data: when the MCP is unavailable the
caller gets one of these exceptions and decides what to do.
"""

from __future__ import annotations


class McpError(Exception):
    """Base class for every MCP failure."""

    code = "MCP_ERROR"


class McpUnavailableError(McpError):
    """The MCP server could not be reached (network, 5xx, timeout)."""

    code = "MCP_UNAVAILABLE"


class McpAuthError(McpError):
    """The MCP rejected our token (401)."""

    code = "MCP_AUTH_ERROR"


class McpCaseNotFoundError(McpError):
    """The requested case does not exist."""

    code = "FINANCIAL_PLAN_NOT_FOUND"


class McpSectionNotFoundError(McpError):
    """The requested section does not exist inside the part."""

    code = "MCP_SECTION_NOT_FOUND"


class McpProtocolError(McpError):
    """The server answered something we cannot parse."""

    code = "MCP_PROTOCOL_ERROR"


class McpEmptyResponseError(McpError):
    """The server answered with an empty payload."""

    code = "MCP_EMPTY_RESPONSE"
