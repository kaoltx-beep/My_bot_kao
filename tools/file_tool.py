from __future__ import annotations

from pathlib import Path

from tools.base import BaseTool, ToolMetadata, ToolResult

ROOT = Path(__file__).resolve().parent.parent


def _safe_path(value: str) -> Path:
    raw = str(value or "").strip().replace("\\", "/")
    path = (ROOT / raw).resolve()
    if path != ROOT and ROOT not in path.parents:
        raise ValueError("path is outside Jarvis project")
    return path


class FileReadTool(BaseTool):
    metadata = ToolMetadata(
        name="file_read",
        version="1.0.0",
        description="อ่านไฟล์ภายใน Jarvis project",
        category="file_system",
        risk_level="low",
        parameters={"required": ["path"]},
    )

    def execute(self, **params):
        path = _safe_path(params.get("path"))
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(str(path.relative_to(ROOT)))
        if path.stat().st_size > 200_000:
            raise ValueError("file too large")
        return ToolResult(success=True, data=path.read_text(encoding="utf-8"))


class FileWriteTool(BaseTool):
    metadata = ToolMetadata(
        name="file_write",
        version="1.0.0",
        description="เขียนไฟล์ภายใน Jarvis project",
        category="file_system",
        risk_level="high",
        require_approval=True,
        can_rollback=True,
        parameters={"required": ["path", "content"]},
    )

    def execute(self, **params):
        path = _safe_path(params.get("path"))
        content = str(params.get("content", ""))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return ToolResult(success=True, data=f"เขียน {path.relative_to(ROOT)} สำเร็จ")


def file_tools() -> list[BaseTool]:
    return [FileReadTool(), FileWriteTool()]
