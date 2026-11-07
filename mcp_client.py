"""Isolated MCP client prototype for Jarvis.

This module is intentionally not wired into the default ToolRegistry.
Remote tool calls require both an explicit per-call approval and an allowlisted
tool name. Only HTTPS endpoints are accepted; plain HTTP is restricted to
loopback for local development.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit


class MCPConfigurationError(ValueError):
    """Raised when an MCP server URL is unsafe or malformed."""


def validate_server_url(server_url: str) -> str:
    """Validate an MCP Streamable HTTP endpoint without making a connection."""
    if not isinstance(server_url, str) or not server_url.strip():
        raise MCPConfigurationError("MCP server URL is required")

    parsed = urlsplit(server_url.strip())
    if parsed.scheme not in {"https", "http"}:
        raise MCPConfigurationError("MCP server URL must use HTTPS")
    if not parsed.hostname or parsed.username or parsed.password:
        raise MCPConfigurationError("MCP server URL must have a host and no embedded credentials")
    if parsed.query or parsed.fragment:
        raise MCPConfigurationError("MCP server URL must not contain a query or fragment")

    host = parsed.hostname.lower()
    loopback_hosts = {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme == "http" and host not in loopback_hosts:
        raise MCPConfigurationError("Plain HTTP is allowed only for local loopback testing")
    return server_url.strip()


def _require_tool_permission(tool_name: str, allowed_tools: set[str], approved: bool) -> None:
    if not approved:
        raise PermissionError("MCP tool calls require explicit user approval")
    if not tool_name or tool_name not in allowed_tools:
        raise PermissionError("MCP tool is not on the configured allowlist")


async def list_server_tools(server_url: str) -> list[dict[str, Any]]:
    """Return tool metadata only; this does not execute remote tools."""
    url = validate_server_url(server_url)
    try:
        from mcp import Client
    except ImportError as exc:
        raise RuntimeError("MCP SDK is not installed; install it with: pip install mcp") from exc

    async with Client(url) as client:
        result = await client.list_tools()
        return [
            {
                "name": tool.name,
                "title": getattr(tool, "title", None),
                "description": getattr(tool, "description", None),
                "input_schema": getattr(tool, "input_schema", {}),
            }
            for tool in result.tools
        ]


async def call_server_tool(
    server_url: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    *,
    allowed_tools: set[str] | None = None,
    approved: bool = False,
) -> dict[str, Any]:
    """Call one explicitly allowlisted MCP tool after approval.

    The caller must obtain approval through Jarvis's existing safety/consent
    flow and pass approved=True. No MCP tool is registered or auto-run by
    this prototype.
    """
    url = validate_server_url(server_url)
    _require_tool_permission(tool_name, allowed_tools or set(), approved)

    try:
        from mcp import Client
    except ImportError as exc:
        raise RuntimeError("MCP SDK is not installed; install it with: pip install mcp") from exc

    async with Client(url) as client:
        result = await client.call_tool(tool_name, arguments or {})
        if result.is_error:
            raise RuntimeError(f"MCP tool failed: {tool_name}")
        return {
            "tool_name": tool_name,
            "structured_content": result.structured_content,
            "content": [
                {"type": getattr(block, "type", "unknown"),
                 "text": getattr(block, "text", None)}
                for block in result.content
            ],
        }
