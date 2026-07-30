from __future__ import annotations

from dataclasses import dataclass

from core.registry import ToolRegistry


@dataclass(frozen=True)
class Route:
    tool_name: str
    confidence: float


DEFAULT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "memory_search": ("จำได้ไหม", "ค้นความจำ", "หาในความจำ", "memory"),
    "memory_store": ("จำไว้", "บันทึกความจำ", "เก็บไว้", "remember"),
    "project_scan": ("สแกนโปรเจกต์", "ดูโครงสร้างโปรเจกต์", "ตรวจโปรเจกต์", "scan project"),
    "file_read": ("อ่านไฟล์", "เปิดไฟล์", "ดูไฟล์", "อ่านโค้ด"),
    "file_write": ("แก้ไฟล์", "เขียนไฟล์", "สร้างไฟล์", "แก้โค้ด"),
    "syntax_check": ("ตรวจ syntax", "เช็ก syntax", "syntax check", "ไวยากรณ์"),
    "test_runner": ("รัน test", "รันทดสอบ", "pytest", "test runner"),
    "git_status": ("git status", "ดูสถานะ git", "สถานะ git"),
    "git_commit": ("git commit", "commit โค้ด", "บันทึกโค้ด"),
    "rollback": ("rollback", "ย้อนกลับ", "ยกเลิกการแก้", "โรลแบ็ก"),
}


class DeterministicRouter:
    """Keyword/category router for V1. No LLM selection yet."""

    def __init__(self, registry: ToolRegistry, keywords: dict[str, tuple[str, ...]] | None = None) -> None:
        self.registry = registry
        self.keywords = keywords or DEFAULT_KEYWORDS

    def route(self, text: str) -> Route | None:
        normalized = (text or "").lower().strip()
        best: Route | None = None
        for tool_name, phrases in self.keywords.items():
            if self.registry.get(tool_name) is None:
                continue
            score = 0.0
            for phrase in phrases:
                if phrase.lower() in normalized:
                    score = max(score, min(1.0, 0.5 + (len(phrase) / max(len(normalized), 1))))
            if score and (best is None or score > best.confidence):
                best = Route(tool_name, score)
        return best
