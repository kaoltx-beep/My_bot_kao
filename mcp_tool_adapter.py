"""Synchronous Jarvis adapter for one explicitly approved MCP tool.

The adapter is intentionally opt-in and is not added to the default registry.
"""
from __future__ import annotations

import asyncio
from typing import Any

from mcp_client import call_server_tool
from tools.base import BaseTool, ToolMetadata, ToolResult


class MCPToolAdapter(BaseTool):
    """Expose one allowlisted MCP tool through Jarvis's synchronous contract."""

    def __init__(
        self,
        *,
        server_url: str,
        tool_name: str,
        allowed_tools: set[str] | frozenset[str],
        timeout_seconds: int = 20,
    ) -> None:
        if not tool_name or tool_name not in allowed_tools:
            raise ValueError("MCP tool must be present in the explicit allowlist")
        if timeout_seconds < 1 or timeout_seconds > 120:
            raise ValueError("timeout_seconds must be between 1 and 120")
        self.server_url = server_url
        self.tool_name = tool_name
        self.allowed_tools = frozenset(allowed_tools)
        self.timeout_seconds = timeout_seconds
        self.metadata = ToolMetadata(
            name=f"mcp:{tool_name}",
            version="1.0.0",
            description=f"Approved MCP tool: {tool_name}",
            category="mcp",
            risk_level="high",
            require_approval=True,
            timeout_seconds=timeout_seconds,
            can_rollback=False,
        )
        super().__init__()

    def execute(self, **params: Any) -> ToolResult:
        # Do not permit callers to bypass ToolExecutor's approval gate.
        return ToolResult(success=False, error="MCP tools must be invoked through ToolExecutor approval")

    def execute_with_approval(self, *, approved: bool, **params: Any) -> ToolResult:
        if not approved:
            return ToolResult(success=False, error="MCP tool call requires explicit Jarvis approval")
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            return ToolResult(
                success=False,
                error="MCP sync adapter cannot run inside an active event loop; use an async integration",
            )

        async def invoke() -> dict[str, Any]:
            return await asyncio.wait_for(
                call_server_tool(
                    self.server_url,
                    self.tool_name,
                    params,
                    allowed_tools=set(self.allowed_tools),
                    approved=True,
                ),
                timeout=self.timeout_seconds,
            )

        try:
            return ToolResult(success=True, data=asyncio.run(invoke()))
        except asyncio.TimeoutError:
            return ToolResult(success=False, error=f"MCP tool timed out after {self.timeout_seconds}s")
        except Exception as exc:
            return ToolResult(success=False, error=f"MCP tool call failed: {type(exc).__name__}")
