from __future__ import annotations

import subprocess
from pathlib import Path

from tools.base import BaseTool, ToolMetadata, ToolResult


ROOT = Path(__file__).resolve().parent.parent

# Local machine configuration must never be swept into an automatic commit.
COMMIT_EXCLUDES = {"config.py"}


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
        version="1.3.0",
        description="stage tracked changes แล้วกันไฟล์ local config ออกจาก commit",
        category="git",
        risk_level="high",
        require_approval=True,
        parameters={"required": ["message"]},
    )

    def execute(self, **params):
        message = str(params.get("message", "")).strip()
        if not message:
            raise ValueError("commit message is required")

        # Never add untracked files. Stage tracked modifications/deletions only.
        _git(["add", "-u"])

        # Explicitly remove machine-local configuration from the index.
        for path in COMMIT_EXCLUDES:
            _git(["restore", "--staged", "--", path])

        staged_paths = [p for p in _git(["diff", "--cached", "--name-only"]).splitlines() if p]
        if not staged_paths:
            raise RuntimeError("ไม่มี tracked changes ที่อนุญาตให้ commit")

        forbidden_staged = sorted(COMMIT_EXCLUDES.intersection(staged_paths))
        if forbidden_staged:
            _git(["restore", "--staged", "--", *forbidden_staged])
            raise RuntimeError(f"blocked files staged: {', '.join(forbidden_staged)}")

        return ToolResult(success=True, data=_git(["commit", "-m", message]))


def git_tools() -> list[BaseTool]:
    return [GitStatusTool(), GitCommitTool()]
