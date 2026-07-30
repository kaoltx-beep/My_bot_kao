"""Jarvis Developer Mode router."""

import re

from dev_handler import handle_dev_request
import developer_mode
import config


_PROJECT_COMMANDS = ("วิเคราะห์โปรเจกต์", "ตรวจโปรเจกต์", "scan โปรเจกต์")
_DEV_KEYWORDS = (
    "วิเคราะห์โปรเจกต์",
    "ตรวจโปรเจกต์",
    "ตรวจ error",
    "ช่วยแก้โค้ด",
    "วิเคราะห์โค้ด",
    "สร้าง patch",
    "แก้โค้ด",
    "แก้ไฟล์",
    "อนุมัติ",
    "ยกเลิก patch",
    "ยกเลิกแพตช์",
)


def is_developer_command(text: str) -> bool:
    normalized = (text or "").lower()
    return any(k in normalized for k in _DEV_KEYWORDS)


def _result_for_run(result: dict) -> dict:
    """Convert workflow results to the response shape expected by run.py."""
    if result.get("files") is not None:
        return result

    if result.get("ok"):
        proposal_id = result.get("proposal_id")
        if proposal_id:
            diff = result.get("diff", "")
            if len(diff) > 2600:
                diff = diff[:2600] + "\n... (ตัด diff ที่เหลือ)"
            text = (
                f"🧩 PATCH PROPOSAL {proposal_id}\n"
                f"ไฟล์: {result.get('file')}\n"
                f"สรุป: {result.get('summary', 'แก้ไขตามคำสั่ง')}\n\n"
                f"{diff}\n\n"
                f"พิมพ์: อนุมัติ {proposal_id}\n"
                f"หรือ: ยกเลิก patch {proposal_id}"
            )
            return {"files": [{"status": "ok", "file": text, "lines": 0}]}
        return {"files": [{"status": "ok", "file": result.get("message", "สำเร็จ"), "lines": 0}]}

    return {"files": [{"status": "error", "file": "Developer Mode", "errors": [result.get("error", "เกิดข้อผิดพลาด")]}]}


def execute_developer_command(text: str, root=".", groq_client=None):
    normalized = (text or "").lower().strip()

    match = re.search(r"อนุมัติ\s+([a-f0-9]{10})", normalized)
    if match:
        return _result_for_run(developer_mode.approve(match.group(1)))

    match = re.search(r"(?:ยกเลิก patch|ยกเลิกแพตช์)\s+([a-f0-9]{10})", normalized)
    if match:
        return _result_for_run(developer_mode.reject(match.group(1)))

    if any(k in normalized for k in _PROJECT_COMMANDS):
        return handle_dev_request(text, root)

    if groq_client is None:
        try:
            from groq import Groq
            groq_client = Groq(api_key=config.GROQ_API_KEY)
        except Exception as exc:
            return _result_for_run({"ok": False, "error": f"เชื่อมต่อ AI ไม่ได้: {exc}"})

    return _result_for_run(developer_mode.handle(text, groq_client=groq_client))
