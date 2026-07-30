from __future__ import annotations

import subprocess
from pathlib import Path

from tools.base import BaseTool, ToolMetadata


ROOT = Path(__file__).resolve().parent.parent


def _git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git command failed")
    return result.stdout.strip()


class GitStatusTool(BaseTool):
    metadata = ToolMetadata(
        name="git_status",
        version="1.0.0",
        description="ตรวจสอบสถานะ Git ของ Jarvis project",
        category="git",
        risk_level="low",
        parameters={"required": []},
    )

    def execute(self, **params):
        from tools.base import ToolResult
        return ToolResult(success=True, data=_git(["status", "--short"]))


class GitCommitTool(BaseTool):
    metadata = ToolMetadata(
        name="git_commit",
        version="1.0.0",
        description="commit ไฟล์ที่ถูก stage แล้วด้วยข้อความที่ระบุ",
        category="git",
        risk_level="high",
        require_approval=True,
        parameters={"required": ["message"]},
    )

    def execute(self, **params):
        from tools.base import ToolResult
        message = str(params.get("message", "")).strip()
        if not message:
            raise ValueError("commit message is required")
        return ToolResult(success=True, data=_git(["commit", "-m", message]))


def git_tools() -> list[BaseTool]:
    return [GitStatusTool(), GitCommitTool()]
