from __future__ import annotations

from typing import Iterable

from tools.base import BaseTool, ToolMetadata


class ToolRegistry:
    """Small in-process registry for Jarvis Tool System V1."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        name = tool.metadata.name.strip()
        if not name:
            raise ValueError("tool name cannot be empty")
        if name in self._tools:
            raise ValueError(f"tool already registered: {name}")
        self._tools[name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list(self) -> list[ToolMetadata]:
        return [tool.metadata for tool in self._tools.values()]

    def filter(self, *, category: str | None = None, risk_level: str | None = None) -> list[BaseTool]:
        tools: Iterable[BaseTool] = self._tools.values()
        if category is not None:
            tools = (tool for tool in tools if tool.metadata.category == category)
        if risk_level is not None:
            tools = (tool for tool in tools if tool.metadata.risk_level == risk_level)
        return list(tools)

    def clear(self) -> None:
        self._tools.clear()

    def __len__(self) -> int:
        return len(self._tools)
