import unittest

from mcp_client import (
    MCPConfigurationError,
    _require_tool_permission,
    validate_server_url,
)


class MCPClientSafetyTests(unittest.TestCase):
    def test_https_remote_endpoint_is_allowed(self):
        self.assertEqual(
            validate_server_url("https://mcp.example.com/mcp"),
            "https://mcp.example.com/mcp",
        )

    def test_loopback_http_is_allowed_for_local_testing(self):
        self.assertEqual(
            validate_server_url("http://127.0.0.1:8000/mcp"),
            "http://127.0.0.1:8000/mcp",
        )

    def test_remote_http_is_rejected(self):
        with self.assertRaises(MCPConfigurationError):
            validate_server_url("http://mcp.example.com/mcp")

    def test_embedded_credentials_are_rejected(self):
        with self.assertRaises(MCPConfigurationError):
            validate_server_url("https://user:secret@mcp.example.com/mcp")

    def test_query_and_fragment_are_rejected(self):
        with self.assertRaises(MCPConfigurationError):
            validate_server_url("https://mcp.example.com/mcp?token=x")

    def test_empty_url_is_rejected(self):
        with self.assertRaises(MCPConfigurationError):
            validate_server_url(" ")

    def test_tool_call_requires_explicit_approval(self):
        with self.assertRaises(PermissionError):
            _require_tool_permission("read_notes", {"read_notes"}, False)

    def test_tool_call_requires_allowlist(self):
        with self.assertRaises(PermissionError):
            _require_tool_permission("delete_data", {"read_notes"}, True)

    def test_approved_allowlisted_tool_is_allowed(self):
        _require_tool_permission("read_notes", {"read_notes"}, True)


if __name__ == "__main__":
    unittest.main()
