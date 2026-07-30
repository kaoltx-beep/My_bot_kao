from __future__ import annotations

import subprocess
from pathlib import Path

from tools.base import BaseTool, ToolMetadata, ToolResult


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
        return ToolResult(success=True, data=_git(["status", "--short"]))


class GitCommitTool(BaseTool):
    metadata = ToolMetadata(
        name="git_commit",
        version="1.1.0",
        description="stage เฉพาะ tracked changes แล้ว commit ด้วยข้อความที่ระบุ",
        category="git",
        risk_level="high",
        require_approval=True,
        parameters={"required": ["message"]},
    )

    def execute(self, **params):
        message = str(params.get("message", "")).strip()
        if not message:
            raise ValueError("commit message is required")

        # Stage only tracked modifications/deletions. Never sweep untracked
        # data/backup files into a commit with `git add .`.
        status = _git(["status", "--short"])
        tracked_changes = [
            line for line in status.splitlines()
            if line and not (line.startswith("??") or line[0:2] == "??")
        ]
        if not tracked_changes:
            raise RuntimeError("ไม่มี tracked changes ให้ commit")

        _git(["add", "-u"])
        staged = _git(["diff", "--cached", "--name-only"])
        if not staged:
            raise RuntimeError("ไม่มีไฟล์ถูก stage หลัง git add -u")

        return ToolResult(success=True, data=_git(["commit", "-m", message]))


def git_tools() -> list[BaseTool]:
    return [GitStatusTool(), GitCommitTool()]
