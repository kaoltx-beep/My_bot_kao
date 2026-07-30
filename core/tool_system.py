from __future__ import annotations

from core.default_registry import build_default_registry
from core.executor import ToolExecutor
from core.router import DeterministicRouter


class JarvisToolSystem:
    """Single V1 facade: registry + deterministic router + safety-gated executor."""

    def __init__(self) -> None:
        self.registry = build_default_registry()
        self.router = DeterministicRouter(self.registry)
        self.executor = ToolExecutor(self.registry)

    def list_tools(self) -> list[str]:
        return [metadata.name for metadata in self.registry.list()]

    def route(self, text: str):
        return self.router.route(text)

    def execute(self, name: str, params: dict | None = None, approved: bool = False):
        return self.executor.execute(name, params=params, approved=approved)
