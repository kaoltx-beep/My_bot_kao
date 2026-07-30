import tempfile
import unittest
from pathlib import Path

from core.default_registry import build_default_registry
from core.params import parse_tool_params
from core.registry import ToolRegistry
from core.router import DeterministicRouter
from core.safety import evaluate
from core.task_chain import TaskChain
from tools.base import BaseTool, ToolMetadata
from tools.file_tool import FileWriteTool


class ToolSystemV1Tests(unittest.TestCase):
    def setUp(self):
        self.registry = ToolRegistry()

        read_tool = BaseTool(lambda path: path)
        read_tool.metadata = ToolMetadata(
            name="file_read",
            version="1.0.0",
            description="Read a file",
            category="file_system",
            risk_level="low",
            parameters={"required": ["path"]},
        )
        self.registry.register(read_tool)

        write_tool = BaseTool(lambda path, content: content)
        write_tool.metadata = ToolMetadata(
            name="file_write",
            version="1.0.0",
            description="Write a file",
            category="file_system",
            risk_level="high",
            require_approval=True,
            parameters={"required": ["path", "content"]},
        )
        self.registry.register(write_tool)

    def test_registry_get_and_filter(self):
        self.assertIsNotNone(self.registry.get("file_read"))
        self.assertEqual(len(self.registry.filter(category="file_system")), 2)
        self.assertEqual(len(self.registry.filter(risk_level="high")), 1)

    def test_default_registry_contains_v1_tools(self):
        registry = build_default_registry()
        names = {metadata.name for metadata in registry.list()}
        expected = {
            "memory_search", "memory_store",
            "expense_add", "expense_list", "expense_monthly",
            "git_status", "git_commit", "git_push",
            "file_read", "file_write",
            "project_scan", "syntax_check", "test_runner",
            "rollback",
        }
        self.assertEqual(names, expected)

    def test_parameter_parser_extracts_python_file(self):
        call = parse_tool_params("file_read", "อ่านไฟล์ run.py")
        self.assertIsNotNone(call)
        self.assertEqual(call.params["path"], "run.py")
        self.assertGreaterEqual(call.confidence, 0.9)

    def test_parameter_parser_extracts_file_write(self):
        call = parse_tool_params("file_write", "แก้ไฟล์ tests/test.py: print('ok')")
        self.assertIsNotNone(call)
        self.assertEqual(call.params["path"], "tests/test.py")
        self.assertEqual(call.params["content"], "print('ok')")

    def test_parameter_parser_extracts_expense(self):
        call = parse_tool_params("expense_add", "น้ำมัน 500 บาท")
        self.assertIsNotNone(call)
        self.assertEqual(call.params["item"], "น้ำมัน")
        self.assertEqual(call.params["amount"], 500.0)

    def test_parameter_parser_extracts_commit_message(self):
        call = parse_tool_params("git_commit", "git commit เพิ่มระบบ Tool")
        self.assertIsNotNone(call)
        self.assertEqual(call.params["message"], "เพิ่มระบบ Tool")

    def test_parameter_parser_extracts_git_push(self):
        call = parse_tool_params("git_push", "git push")
        self.assertIsNotNone(call)
        self.assertEqual(call.params, {})

    def test_parameter_parser_rejects_missing_required_value(self):
        self.assertIsNone(parse_tool_params("file_read", "อ่านไฟล์"))
        self.assertIsNone(parse_tool_params("file_write", "แก้ไฟล์ run.py"))
        self.assertIsNone(parse_tool_params("memory_store", "จำไว้"))

    def test_file_write_metadata_requires_approval(self):
        self.assertEqual(FileWriteTool.metadata.risk_level, "high")
        self.assertTrue(FileWriteTool.metadata.require_approval)
        self.assertTrue(FileWriteTool.metadata.can_rollback)

    def test_task_chain_is_bounded_and_persistent(self):
        chain = TaskChain(max_steps=2)
        events = []
        result = chain.run(
            "test chain",
            [("one", lambda: events.append("one")), ("two", lambda: events.append("two")), ("three", lambda: events.append("three"))],
        )
        self.assertEqual(events, ["one", "two"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["step"], 2)

    def test_duplicate_registration_is_rejected(self):
        with self.assertRaises(ValueError):
            self.registry.register(self.registry.get("file_read"))

    def test_safety_low_runs_without_approval(self):
        decision = evaluate("low")
        self.assertTrue(decision.allowed)
        self.assertFalse(decision.requires_approval)

    def test_safety_high_requires_approval(self):
        decision = evaluate("high")
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_approval)
        self.assertTrue(evaluate("high", approved=True).allowed)

    def test_router_uses_registered_tools_only(self):
        router = DeterministicRouter(self.registry)
        route = router.route("ช่วยอ่านไฟล์ run.py")
        self.assertIsNotNone(route)
        self.assertEqual(route.tool_name, "file_read")
        self.assertIsNone(router.route("ค้นหาเว็บข่าวล่าสุด"))


if __name__ == "__main__":
    unittest.main()

# Approval Commit Test

# Git commit approval test

# Git push approval test
