from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class ToolMetadata:
    name: str
    version: str
    description: str
    category: str
    risk_level: str = "low"
    require_approval: bool = False
    timeout_seconds: int = 30
    can_rollback: bool = False
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str | None = None
    duration_ms: int = 0


class BaseTool:
    """Minimal Tool contract used by Jarvis Tool System V1."""

    metadata: ToolMetadata

    def __init__(self, handler: Callable[..., Any] | None = None):
        self._handler = handler

    def validate(self, params: dict[str, Any]) -> None:
        required = self.metadata.parameters.get("required", [])
        missing = [key for key in required if key not in params]
        if missing:
            raise ValueError(f"missing parameters: {', '.join(missing)}")

    def execute(self, **params: Any) -> ToolResult:
        self.validate(params)
        if self._handler is None:
            raise NotImplementedError(f"tool handler not configured: {self.metadata.name}")
        return ToolResult(success=True, data=self._handler(**params))
