import unittest

import developer_mode


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

    def test_non_code_extension_is_blocked(self):
        with self.assertRaises(ValueError):
            developer_mode._safe_path("notes.exe")

    def test_code_fence_cleanup(self):
        cleaned = developer_mode._clean_model_code("```python\nprint('ok')\n```")
        self.assertEqual(cleaned, "print('ok')\n")


if __name__ == "__main__":
    unittest.main()
