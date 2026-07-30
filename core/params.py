from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ParsedToolCall:
    tool_name: str
    params: dict[str, Any]
    confidence: float


_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:[\\/]")


def _clean_path(text: str) -> str:
    value = text.strip().strip('`\"\'')
    value = value.rstrip(" .,")
    if not _WINDOWS_DRIVE.match(value):
        value = value.lstrip("./") or value
    return value


def parse_tool_params(tool_name: str, text: str) -> ParsedToolCall | None:
    normalized = (text or "").strip()

    if tool_name in {"file_read", "syntax_check"}:
        patterns = [
            r"(?:อ่าน|เปิด|ดู)\s*(?:ไฟล์|โค้ด)?\s*([\w./-]+\.py)",
            r"(?:ตรวจ|เช็ก)\s*(?:syntax\s*)?(?:ไฟล์\s*)?([\w./-]+\.py)",
            r"(?:file|path)\s*[:=]\s*([\w./-]+\.py)",
        ]
        for pattern in patterns:
            match = re.search(pattern, normalized, re.IGNORECASE)
            if match:
                return ParsedToolCall(tool_name, {"path": _clean_path(match.group(1))}, 0.95)
        return None

    if tool_name == "project_scan":
        return ParsedToolCall(tool_name, {}, 0.95)

    if tool_name == "test_runner":
        return ParsedToolCall(tool_name, {}, 0.90)

    if tool_name == "memory_search":
        limit_match = re.search(r"(?:ล่าสุด|last)\s*(\d+)", normalized, re.IGNORECASE)
        limit = max(1, min(int(limit_match.group(1)), 50)) if limit_match else 5
        return ParsedToolCall(tool_name, {"limit": limit}, 0.90)

    if tool_name == "memory_store":
        match = re.search(r"(?:จำไว้|บันทึกความจำ|จำว่า)\s*([^:：=]+?)\s*[:：=]\s*(.+)$", normalized)
        if match:
            return ParsedToolCall(tool_name, {"key": match.group(1).strip(), "value": match.group(2).strip()}, 0.95)
        return None

    if tool_name == "expense_add":
        match = re.search(r"(.+?)\s+(\d+(?:\.\d+)?)\s*(?:บาท|บ\.?)?$", normalized)
        if match:
            return ParsedToolCall(tool_name, {"item": match.group(1).strip(), "amount": float(match.group(2))}, 0.95)
        return None

    if tool_name == "expense_list" or tool_name == "expense_monthly" or tool_name == "git_status":
        return ParsedToolCall(tool_name, {}, 0.95)

    if tool_name == "git_commit":
        match = re.search(r"(?:git\s+commit|commit)\s*(?:ว่า|ข้อความ|message)?\s*[:：]?\s*(.+)$", normalized, re.IGNORECASE)
        if match:
            return ParsedToolCall(tool_name, {"message": match.group(1).strip()}, 0.90)
        return None

    if tool_name == "rollback":
        match = re.search(r"(?:rollback|โรลแบ็ก|ย้อนกลับ)(?:\s+patch)?\s+([a-f0-9]{10})\b", normalized, re.IGNORECASE)
        if match:
            return ParsedToolCall(tool_name, {"proposal_id": match.group(1)}, 0.98)
        return None

    return ParsedToolCall(tool_name, {}, 0.50)
