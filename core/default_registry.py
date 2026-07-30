from __future__ import annotations

from core.registry import ToolRegistry
from tools.code_tool import code_tools
from tools.expense_tool import expense_tools
from tools.file_tool import file_tools
from tools.git_tool import git_tools
from tools.memory_tool import memory_tools
from tools.rollback_tool import rollback_tools


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    tools = [
        *memory_tools(),
        *expense_tools(),
        *git_tools(),
        *file_tools(),
        *code_tools(),
        *rollback_tools(),
    ]
    for tool in tools:
        registry.register(tool)
    return registry
