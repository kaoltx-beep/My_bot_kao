import os
import unittest
from unittest.mock import patch

from mcp_client import (
    MCPConfigurationError,
    _require_tool_permission,
    _serialize_content_block,
    _github_access_token,
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

    def test_github_remote_endpoint_must_be_read_only(self):
        self.assertEqual(
            validate_server_url("https://api.githubcopilot.com/mcp/readonly"),
            "https://api.githubcopilot.com/mcp/readonly",
        )
        with self.assertRaises(MCPConfigurationError):
            validate_server_url("https://api.githubcopilot.com/mcp/")

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

    def test_github_token_can_be_supplied_without_persisting_it(self):
        with patch.dict(os.environ, {"GITHUB_PERSONAL_ACCESS_TOKEN": "unit-test-token"}):
            self.assertEqual(_github_access_token(), "unit-test-token")

    def test_content_serializer_preserves_text_blocks(self):
        class TextBlock:
            type = "text"
            text = "ok"

        self.assertEqual(
            _serialize_content_block(TextBlock()),
            {"type": "text", "text": "ok"},
        )

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
