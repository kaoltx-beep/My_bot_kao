import unittest
from unittest.mock import patch

import developer_mode
import developer_mode_router


class DeveloperModeTests(unittest.TestCase):
    def test_analyze_existing_python_file(self):
        result = developer_mode.analyze_file("run.py")
        self.assertTrue(result["ok"])
        self.assertGreater(result["lines"], 0)

    def test_path_traversal_is_blocked(self):
        with self.assertRaises(ValueError):
            developer_mode._safe_path("../run.py")

    def test_protected_config_is_blocked(self):
        with self.assertRaises(ValueError):
            developer_mode._safe_path("config.py")

    def test_nested_env_file_is_blocked(self):
        with self.assertRaises(ValueError):
            developer_mode._safe_path("settings/.env.production")

    def test_hidden_directory_is_blocked(self):
        with self.assertRaises(ValueError):
            developer_mode._safe_path(".github/workflows/test.yml")

    def test_approval_fails_closed_without_admin_id(self):
        self.assertFalse(developer_mode._is_authorized_admin(None, "12345"))
        self.assertFalse(developer_mode._is_authorized_admin(67890, "12345"))

    def test_approval_allows_only_configured_admin_id(self):
        self.assertTrue(developer_mode._is_authorized_admin(12345, "12345,99999"))

    def test_non_code_extension_is_blocked(self):
        with self.assertRaises(ValueError):
            developer_mode._safe_path("notes.exe")

    def test_code_fence_cleanup(self):
        cleaned = developer_mode._clean_model_code("```python\nprint('ok')\n```")
        self.assertEqual(cleaned, "print('ok')\n")

    @patch("developer_mode_router.developer_mode.approve")
    def test_router_forwards_telegram_actor_id(self, approve_mock):
        approve_mock.return_value = {"ok": False, "error": "test"}
        developer_mode_router.execute_developer_command(
            "อนุมัติ abcdef1234", actor_id=123456789
        )
        approve_mock.assert_called_once_with("abcdef1234", actor_id=123456789)

    def test_developer_session_file_is_protected(self):
        with self.assertRaises(ValueError):
            developer_mode._safe_path("data/developer_session.json")


if __name__ == "__main__":
    unittest.main()
