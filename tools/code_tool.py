from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

from tools.base import BaseTool, ToolMetadata, ToolResult

ROOT = Path(__file__).resolve().parent.parent


def _safe_py_path(value: str) -> Path:
    path = (ROOT / str(value or "").strip().replace("\\", "/")).resolve()
    if path != ROOT and ROOT not in path.parents:
        raise ValueError("path is outside Jarvis project")
    if path.suffix != ".py":
        raise ValueError("only Python files are supported")
    return path


class ProjectScanTool(BaseTool):
    metadata = ToolMetadata(
        name="project_scan",
        version="1.0.0",
        description="สแกนไฟล์ใน Jarvis project",
        category="project",
        risk_level="low",
        parameters={"required": []},
    )

    def execute(self, **params):
        files = []
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if any(part in {".git", "__pycache__"} for part in path.parts):
                continue
            files.append(str(path.relative_to(ROOT)))
            if len(files) >= 300:
                break
        return ToolResult(success=True, data=files)


class SyntaxCheckTool(BaseTool):
    metadata = ToolMetadata(
        name="syntax_check",
        version="1.0.0",
        description="ตรวจสอบ syntax ของไฟล์ Python",
        category="code",
        risk_level="low",
        parameters={"required": ["path"]},
    )

    def execute(self, **params):
        path = _safe_py_path(params.get("path"))
        if not path.exists():
            raise FileNotFoundError(str(path.relative_to(ROOT)))
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            return ToolResult(success=True, data=f"✅ syntax OK: {path.relative_to(ROOT)}")
        except SyntaxError as exc:
            return ToolResult(success=False, error=f"line {exc.lineno}: {exc.msg}")


class TestRunnerTool(BaseTool):
    metadata = ToolMetadata(
        name="test_runner",
        version="1.0.0",
        description="รัน unittest ของ Jarvis และคืนผลการทดสอบ",
        category="test",
        # V1: this runner only executes the project's unittest suite.
        # It does not accept arbitrary shell commands and remains bounded by timeout.
        risk_level="low",
        timeout_seconds=60,
        parameters={"required": []},
    )

    def execute(self, **params):
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = (result.stdout + "\n" + result.stderr).strip()
        return ToolResult(success=result.returncode == 0, data=output[-6000:])


def code_tools() -> list[BaseTool]:
    return [ProjectScanTool(), SyntaxCheckTool(), TestRunnerTool()]
