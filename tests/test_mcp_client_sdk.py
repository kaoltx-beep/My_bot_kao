"""Integration checks against the official MCP Python SDK v2.

The SDK Client is connected to an in-memory MCPServer, so tests need no
network listener, credentials, production service, or external MCP endpoint.
"""
import unittest
from unittest.mock import patch

from mcp import Client
from mcp.server import MCPServer

from mcp_client import call_server_tool, list_server_tools


class MCPClientSDKIntegrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.server = MCPServer("Jarvis MCP test server")

        @self.server.tool()
        def read_status() -> int:
            """Return a harmless test status."""
            return 7

    def _client_for_test_server(self, _url):
        return Client(self.server, raise_exceptions=True)

    async def test_list_tools_uses_real_sdk_client(self):
        with patch("mcp.Client", side_effect=self._client_for_test_server):
            tools = await list_server_tools("http://127.0.0.1:8000/mcp")

        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], "read_status")
        self.assertIn("input_schema", tools[0])

    async def test_call_tool_uses_real_sdk_client_and_enforces_approval(self):
        with self.assertRaises(PermissionError):
            await call_server_tool(
                "http://127.0.0.1:8000/mcp",
                "read_status",
                allowed_tools={"read_status"},
                approved=False,
            )

        with patch("mcp.Client", side_effect=self._client_for_test_server):
            result = await call_server_tool(
                "http://127.0.0.1:8000/mcp",
                "read_status",
                allowed_tools={"read_status"},
                approved=True,
            )

        self.assertEqual(result["tool_name"], "read_status")
        self.assertEqual(result["structured_content"], {"result": 7})
        self.assertFalse(any(item.get("type") == "error" for item in result["content"]))


if __name__ == "__main__":
    unittest.main()
