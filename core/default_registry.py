from __future__ import annotations

from core.registry import ToolRegistry
from tools.expense_tool import expense_tools
from tools.git_tool import git_tools
from tools.memory_tool import memory_tools


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for tool in [*memory_tools(), *expense_tools(), *git_tools()]:
        registry.register(tool)
    return registry
