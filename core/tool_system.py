from __future__ import annotations

from core.default_registry import build_default_registry
from core.executor import ToolExecutor
from core.params import ParsedToolCall, parse_tool_params
from core.router import DeterministicRouter


class JarvisToolSystem:
    """Single V1 facade: registry + router + parameter parser + safety executor."""

    def __init__(self) -> None:
        self.registry = build_default_registry()
        self.router = DeterministicRouter(self.registry)
        self.executor = ToolExecutor(self.registry)

    def list_tools(self) -> list[str]:
        return [metadata.name for metadata in self.registry.list()]

    def route(self, text: str):
        return self.router.route(text)

    def parse(self, text: str) -> ParsedToolCall | None:
        route = self.route(text)
        if route is None:
            return None
        return parse_tool_params(route.tool_name, text)

    def execute(self, name: str, params: dict | None = None, approved: bool = False):
        return self.executor.execute(name, params=params, approved=approved)

    def execute_text(self, text: str, approved: bool = False):
        call = self.parse(text)
        if call is None:
            return None, "ไม่สามารถแยก Tool หรือพารามิเตอร์จากคำสั่งได้"
        return call, self.execute(call.tool_name, call.params, approved=approved)
