import json
import unittest
from unittest.mock import patch

import developer_mode


class DeveloperModeTests(unittest.TestCase):
    def setUp(self):
        self.target = developer_mode.PROJECT_ROOT / "tests" / "_devmode_target.txt"
        self.session_path = developer_mode.PROJECT_ROOT / "tests" / "_devmode_session.json"
        self.target.write_text("original\n", encoding="utf-8")
        self.addCleanup(self._cleanup)
        self.original_session_file = developer_mode.SESSION_FILE
        developer_mode.SESSION_FILE = self.session_path

    def _cleanup(self):
        developer_mode.SESSION_FILE = self.original_session_file
        self.target.unlink(missing_ok=True)
        self.session_path.unlink(missing_ok=True)
        for backup in self.target.parent.glob(self.target.name + ".backup_*"):
            backup.unlink(missing_ok=True)

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

    def _write_proposal(self, proposal):
        self.session_path.write_text(json.dumps(proposal), encoding="utf-8")

    def test_approve_applies_and_commits(self):
        self._write_proposal({
            "id": "abc123def4",
            "status": "pending",
            "file": "tests/_devmode_target.txt",
            "summary": "update test target",
            "original": "original\n",
            "new_content": "updated\n",
            "diff": "",
        })

        def fake_run(args, **kwargs):
            if args[:2] == ["git", "status"]:
                self.assertEqual(kwargs.get("cwd"), developer_mode.PROJECT_ROOT)
                return type("Result", (), {"returncode": 0, "stdout": " M tests/_devmode_target.txt", "stderr": ""})()
            if args[:2] == ["git", "add"]:
                self.assertEqual(kwargs.get("cwd"), developer_mode.PROJECT_ROOT)
                return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            if args[:2] == ["git", "commit"]:
                self.assertEqual(kwargs.get("cwd"), developer_mode.PROJECT_ROOT)
                return type("Result", (), {"returncode": 0, "stdout": "[main 1234567] test commit", "stderr": ""})()
            raise AssertionError(f"unexpected subprocess call: {args}")

        with patch.object(developer_mode.subprocess, "run", side_effect=fake_run):
            result = developer_mode.approve("abc123def4")

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "committed")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "updated\n")
        self.assertFalse(list(self.target.parent.glob(self.target.name + ".backup_*")))
        saved = json.loads(self.session_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["status"], "committed")

    def test_approve_marks_tested_uncommitted_when_git_commit_fails(self):
        self._write_proposal({
            "id": "fedcba9876",
            "status": "pending",
            "file": "tests/_devmode_target.txt",
            "summary": "update without commit",
            "original": "original\n",
            "new_content": "updated without commit\n",
            "diff": "",
        })

        def fake_run(args, **kwargs):
            if args[:2] == ["git", "status"]:
                return type("Result", (), {"returncode": 0, "stdout": " M tests/_devmode_target.txt", "stderr": ""})()
            if args[:2] == ["git", "add"]:
                return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            if args[:2] == ["git", "commit"]:
                return type("Result", (), {"returncode": 1, "stdout": "", "stderr": "nothing to commit"})()
            raise AssertionError(f"unexpected subprocess call: {args}")

        with patch.object(developer_mode.subprocess, "run", side_effect=fake_run):
            result = developer_mode.approve("fedcba9876")

        self.assertFalse(result["ok"])
        self.assertIn("commit ไม่สำเร็จ", result["error"])
        self.assertEqual(self.target.read_text(encoding="utf-8"), "updated without commit\n")
        saved = json.loads(self.session_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["status"], "tested_uncommitted")
        self.assertIn("commit_error", saved)
        self.assertEqual(len(list(self.target.parent.glob(self.target.name + ".backup_*"))), 1)

    def test_approve_rolls_back_on_syntax_failure(self):
        target = developer_mode.PROJECT_ROOT / "tests" / "_devmode_target.py"
        session_path = developer_mode.PROJECT_ROOT / "tests" / "_devmode_py_session.json"
        target.write_text("print('original')\n", encoding="utf-8")
        proposal = {
            "id": "deadbeef01",
            "status": "pending",
            "file": "tests/_devmode_target.py",
            "summary": "broken syntax",
            "original": "print('original')\n",
            "new_content": "def broken(:\n",
            "diff": "",
        }
        session_path.write_text(json.dumps(proposal), encoding="utf-8")
        previous_session = developer_mode.SESSION_FILE
        developer_mode.SESSION_FILE = session_path
        self.addCleanup(lambda: setattr(developer_mode, "SESSION_FILE", previous_session))
        self.addCleanup(lambda: session_path.unlink(missing_ok=True))
        self.addCleanup(lambda: target.unlink(missing_ok=True))
        for backup in target.parent.glob(target.name + ".backup_*"):
            backup.unlink(missing_ok=True)

        result = developer_mode.approve("deadbeef01")

        self.assertFalse(result["ok"])
        self.assertIn("rollback", result["error"])
        self.assertEqual(target.read_text(encoding="utf-8"), "print('original')\n")
        self.assertFalse(list(target.parent.glob(target.name + ".backup_*")))
        saved = json.loads(session_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["status"], "rolled_back")


if __name__ == "__main__":
    unittest.main()
