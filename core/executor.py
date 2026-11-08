from __future__ import annotations

import time
from typing import Any

from core.registry import ToolRegistry
from core.safety import evaluate
from tools.base import ToolResult


class ToolExecutor:
    """V1 executor: safety gate first, then run a registered tool."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute(
        self,
        name: str,
        params: dict[str, Any] | None = None,
        approved: bool = False,
        approval_grant: str | None = None,
    ) -> ToolResult:
        tool = self.registry.get(name)
        if tool is None:
            return ToolResult(success=False, error=f"unknown tool: {name}")

        decision = evaluate(tool.metadata.risk_level, approved=approved)
        if not decision.allowed:
            return ToolResult(success=False, error=decision.reason)

        approved_executor = getattr(tool, "execute_with_approval", None)
        if callable(approved_executor) and not approval_grant:
            return ToolResult(success=False, error="approval grant required; a boolean approval is not sufficient")

        started = time.perf_counter()
        try:
            if callable(approved_executor):
                result = approved_executor(approved=approved, approval_grant=approval_grant, **(params or {}))
            else:
                result = tool.execute(**(params or {}))
            result.duration_ms = int((time.perf_counter() - started) * 1000)
            return result
        except Exception as exc:
            return ToolResult(
                success=False,
                error=str(exc),
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
