import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from core import approval

from core.executor import ToolExecutor
from core.registry import ToolRegistry
from mcp_tool_adapter import MCPToolAdapter


def _make_grant(params):
    approval.STORE.parent.mkdir(parents=True, exist_ok=True)
    approval_id = approval.create(
        "mcp:read_status", params, chat_id=-100123, user_id=456
    )
    item = approval.consume(
        approval_id, "approved", chat_id=-100123, user_id=456
    )
    return item["approval_grant"]


class MCPToolAdapterTests(unittest.TestCase):
    def make_adapter(self):
        return MCPToolAdapter(
            server_url="http://127.0.0.1:8000/mcp",
            tool_name="read_status",
            allowed_tools={"read_status"},
            timeout_seconds=3,
        )

    def test_adapter_is_high_risk_and_requires_approval(self):
        adapter = self.make_adapter()
        self.assertEqual(adapter.metadata.risk_level, "high")
        self.assertTrue(adapter.metadata.require_approval)

    def test_direct_execute_cannot_bypass_executor(self):
        result = self.make_adapter().execute()
        self.assertFalse(result.success)
        self.assertIn("ToolExecutor", result.error)

    def test_executor_blocks_without_approval_and_does_not_call_mcp(self):
        registry = ToolRegistry()
        registry.register(self.make_adapter())
        with patch("mcp_tool_adapter.call_server_tool", new_callable=AsyncMock) as call:
            result = ToolExecutor(registry).execute("mcp:read_status", {})
        self.assertFalse(result.success)
        self.assertIn("requires approval", result.error)
        call.assert_not_awaited()

    def test_boolean_approval_without_grant_is_rejected(self):
        registry = ToolRegistry()
        registry.register(self.make_adapter())
        with patch("mcp_tool_adapter.call_server_tool", new_callable=AsyncMock) as call:
            result = ToolExecutor(registry).execute(
                "mcp:read_status", {"detail": "brief"}, approved=True
            )
        self.assertFalse(result.success)
        self.assertIn("approval grant required", result.error)
        call.assert_not_awaited()

    def test_executor_passes_verified_approval_grant_to_adapter(self):
        expected = {"tool_name": "read_status", "structured_content": {"result": 7}, "content": []}
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(approval, "STORE", Path(tmp) / "approvals.json"):
                params = {"detail": "brief"}
                grant = _make_grant(params)
                registry = ToolRegistry()
                registry.register(self.make_adapter())
                with patch("mcp_tool_adapter.call_server_tool", new_callable=AsyncMock, return_value=expected) as call:
                    result = ToolExecutor(registry).execute(
                        "mcp:read_status", params, approved=True, approval_grant=grant
                    )
                self.assertTrue(result.success)
                self.assertEqual(result.data, expected)
                call.assert_awaited_once_with(
            "http://127.0.0.1:8000/mcp",
            "read_status",
            {"detail": "brief"},
            allowed_tools={"read_status"},
            approved=True,
        )

    def test_adapter_rejects_tool_not_on_allowlist(self):
        with self.assertRaises(ValueError):
            MCPToolAdapter(
                server_url="https://mcp.example.com/mcp",
                tool_name="delete_everything",
                allowed_tools={"read_status"},
            )


try:
    from mcp import Client
    from mcp.server import MCPServer
except ImportError:
    Client = None
    MCPServer = None


@unittest.skipIf(Client is None, "MCP SDK integration runs in isolated environment")
class MCPToolAdapterSDKIntegrationTests(unittest.TestCase):
    def test_approved_adapter_calls_in_memory_read_only_mcp_server(self):
        server = MCPServer("Jarvis read-only adapter test")

        @server.tool()
        def read_status() -> int:
            """Read a harmless status value; this tool does not mutate state."""
            return 7

        registry = ToolRegistry()
        registry.register(
            MCPToolAdapter(
                server_url="http://127.0.0.1:8000/mcp",
                tool_name="read_status",
                allowed_tools={"read_status"},
                timeout_seconds=3,
            )
        )

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(approval, "STORE", Path(tmp) / "approvals.json"):
                grant = _make_grant({})
                with patch("mcp.Client", side_effect=lambda _url: Client(server, raise_exceptions=True)):
                    result = ToolExecutor(registry).execute(
                        "mcp:read_status",
                        {},
                        approved=True,
                        approval_grant=grant,
                    )

        self.assertTrue(result.success, result.error)
        self.assertEqual(result.data["tool_name"], "read_status")
        self.assertEqual(result.data["structured_content"], {"result": 7})


if __name__ == "__main__":
    unittest.main()
