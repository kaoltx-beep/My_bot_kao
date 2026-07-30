import unittest

from core.registry import ToolRegistry
from core.router import DeterministicRouter
from core.safety import evaluate
from tools.base import BaseTool, ToolMetadata


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
