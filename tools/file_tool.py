from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from tools.base import BaseTool, ToolMetadata, ToolResult

ROOT = Path(__file__).resolve().parent.parent
BACKUP_ROOT = ROOT / "data" / "tool_backups"


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
        version="1.1.0",
        description="เขียนไฟล์ภายใน Jarvis project พร้อม backup อัตโนมัติ",
        category="file_system",
        risk_level="high",
        require_approval=True,
        can_rollback=True,
        parameters={"required": ["path", "content"]},
    )

    def execute(self, **params):
        path = _safe_path(params.get("path"))
        content = str(params.get("content", ""))
        if len(content) > 200_000:
            raise ValueError("content too large")

        BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
        backup_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        relative = path.relative_to(ROOT)
        backup_path = BACKUP_ROOT / f"{backup_id}__{relative.as_posix().replace('/', '__')}"

        existed = path.exists()
        if existed:
            if not path.is_file():
                raise ValueError("target is not a regular file")
            shutil.copy2(path, backup_path)
        else:
            backup_path.write_text("", encoding="utf-8")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return ToolResult(
            success=True,
            data={
                "message": f"เขียน {relative} สำเร็จ",
                "path": str(relative),
                "backup_id": backup_id,
                "backup_path": str(backup_path.relative_to(ROOT)),
                "existed_before": existed,
            },
        )


def file_tools() -> list[BaseTool]:
    return [FileReadTool(), FileWriteTool()]
