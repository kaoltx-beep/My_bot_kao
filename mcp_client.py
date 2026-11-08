"""Isolated MCP client for Jarvis.

GitHub's hosted endpoint is restricted to read-only URLs. Credentials are
loaded from GITHUB_PERSONAL_ACCESS_TOKEN or the local `gh auth token` helper;
they are never written to disk or included in logs.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator
from urllib.parse import urlsplit


GITHUB_MCP_DEFAULT_URL = "https://api.githubcopilot.com/mcp/readonly"
GITHUB_MCP_HOST = "api.githubcopilot.com"


class MCPConfigurationError(ValueError):
    """Raised when an MCP server URL is unsafe or malformed."""


def validate_server_url(server_url: str) -> str:
    """Validate an MCP Streamable HTTP endpoint without making a connection."""
    if not isinstance(server_url, str) or not server_url.strip():
        raise MCPConfigurationError("MCP server URL is required")

    url = server_url.strip()
    parsed = urlsplit(url)
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
    if host == GITHUB_MCP_HOST and not parsed.path.rstrip("/").endswith("/readonly"):
        raise MCPConfigurationError("GitHub MCP must use a read-only endpoint")
    return url


def _github_access_token() -> str:
    """Read a token from the environment or existing GitHub CLI login."""
    token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "").strip()
    if token:
        return token

    gh = shutil.which("gh")
    if not gh:
        raise RuntimeError(
            "GitHub MCP needs GITHUB_PERSONAL_ACCESS_TOKEN or an authenticated GitHub CLI (gh auth login)"
        )
    try:
        result = subprocess.run(
            [gh, "auth", "token"],
            check=True,
            capture_output=True,
            text=True,
            timeout=8,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        raise RuntimeError("Could not obtain GitHub credentials from the local GitHub CLI") from exc
    token = result.stdout.strip()
    if not token:
        raise RuntimeError("GitHub CLI returned no authentication token")
    return token


@asynccontextmanager
async def _connected_client(url: str) -> AsyncIterator[Any]:
    """Yield an MCP session; GitHub uses authenticated Streamable HTTP."""
    try:
        from mcp import Client
    except ImportError as exc:
        raise RuntimeError("MCP SDK is not installed; install it with: pip install mcp") from exc

    parsed = urlsplit(url)
    if parsed.hostname and parsed.hostname.lower() == GITHUB_MCP_HOST:
        try:
            from mcp.client.session import ClientSession
            from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client
        except ImportError as exc:
            raise RuntimeError("Installed MCP SDK lacks Streamable HTTP client support") from exc

        http_client = create_mcp_http_client(
            headers={"Authorization": f"Bearer {_github_access_token()}"}
        )
        async with http_client:
            async with streamable_http_client(url, http_client=http_client) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    yield session
        return

    async with Client(url) as session:
        yield session


def _serialize_content_block(block: Any) -> dict[str, Any]:
    """Preserve text, embedded resources, and other MCP content block data."""
    dump = getattr(block, "model_dump", None)
    if callable(dump):
        return dump(mode="json", exclude_none=True)
    return {
        "type": getattr(block, "type", "unknown"),
        "text": getattr(block, "text", None),
    }


def _require_tool_permission(tool_name: str, allowed_tools: set[str], approved: bool) -> None:
    if not approved:
        raise PermissionError("MCP tool calls require explicit user approval")
    if not tool_name or tool_name not in allowed_tools:
        raise PermissionError("MCP tool is not on the configured allowlist")


async def list_server_tools(server_url: str = GITHUB_MCP_DEFAULT_URL) -> list[dict[str, Any]]:
    """Return tool metadata only; this does not execute remote tools."""
    url = validate_server_url(server_url)
    async with _connected_client(url) as client:
        result = await client.list_tools()
        return [
            {
                "name": tool.name,
                "title": getattr(tool, "title", None),
                "description": getattr(tool, "description", None),
                "input_schema": getattr(tool, "input_schema", {}),
                "read_only": bool(
                    getattr(getattr(tool, "annotations", None), "read_only_hint", False)
                ),
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
    """Call one explicitly allowlisted MCP tool after approval."""
    url = validate_server_url(server_url)
    _require_tool_permission(tool_name, allowed_tools or set(), approved)

    async with _connected_client(url) as client:
        result = await client.call_tool(tool_name, arguments or {})
        if result.is_error:
            raise RuntimeError(f"MCP tool failed: {tool_name}")
        return {
            "tool_name": tool_name,
            "structured_content": result.structured_content,
            "content": [_serialize_content_block(block) for block in result.content],
        }
