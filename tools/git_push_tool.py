from __future__ import annotations

from tools.base import BaseTool, ToolMetadata, ToolResult
from tools.git_tool import _git


class GitPushTool(BaseTool):
    metadata = ToolMetadata(
        name="git_push",
        version="1.0.0",
        description="push branch ปัจจุบันขึ้น origin",
        category="git",
        risk_level="high",
        require_approval=True,
        timeout_seconds=60,
        parameters={"required": []},
    )

    def execute(self, **params):
        return ToolResult(success=True, data=_git(["push", "origin", "HEAD"]))


def git_push_tools() -> list[BaseTool]:
    return [GitPushTool()]
