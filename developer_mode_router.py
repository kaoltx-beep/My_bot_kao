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
    "ดำเนินการ",
    "ดำเนินการต่อ",
    "สถานะระบบ",
    "/status",
    "ทดสอบ rollback",
    "ทดสอบโรลแบ็ก",
    "rollback",
    "โรลแบ็ก",
)


def is_developer_command(text: str) -> bool:
    normalized = (text or "").lower()
    return any(k in normalized for k in _DEV_KEYWORDS)


def _result_for_run(result: dict) -> dict:
    """Convert workflow results to the response shape expected by run.py."""
    if result.get("files") is not None:
        return result

    if result.get("ok"):
        status = result.get("status")
        if status == "committed":
            file_name = result.get("file") or result.get("details") or "ไฟล์ที่แก้ไข"
            return {"files": [{"status": "ok", "file": f"✅ แก้ไข → ทดสอบ → commit สำเร็จ\n📝 {file_name}", "lines": 1}]}
        if status == "rolled_back":
            message = result.get("message") or "แก้ไขไม่ผ่าน จึง rollback กลับเป็นไฟล์เดิมแล้ว"
            return {"files": [{"status": "ok", "file": f"✅ {message}", "lines": 1}]}
        if status == "tested_uncommitted":
            return {"files": [{"status": "error", "file": result.get("file", "Developer Mode"), "errors": ["แก้ไขและทดสอบผ่านแล้ว แต่ commit ไม่สำเร็จ"]}]}
        if status == "rejected":
            return {"files": [{"status": "ok", "file": "✅ ยกเลิก patch แล้ว", "lines": 1}]}

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

        if result.get("file"):
            return {
                "files": [{
                    "status": "ok",
                    "file": result["file"],
                    "lines": result.get("lines", 0),
                }]
            }

        return {"files": [{"status": "ok", "file": result.get("message", "สำเร็จ"), "lines": 1}]}

    return {"files": [{"status": "error", "file": "Developer Mode", "errors": [result.get("error", "เกิดข้อผิดพลาด")]}]}


def _get_groq_client(groq_client=None):
    if groq_client is not None:
        return groq_client
    try:
        from groq import Groq
        return Groq(api_key=config.GROQ_API_KEY)
    except Exception as exc:
        return exc


def _execute_auto(text: str, groq_client=None):
    """Run Developer Mode end-to-end without a manual approval step."""
    normalized = (text or "").strip()
    remainder = re.sub(r"^(?:ดำเนินการต่อ|ดำเนินการ)\s*", "", normalized, count=1).strip()

    proposal = developer_mode._load_session()
    if not remainder and proposal.get("id") and proposal.get("status") == "pending":
        return _result_for_run(developer_mode.approve(proposal["id"]))

    if not remainder:
        return _result_for_run({"ok": False, "error": "โหมดอัตโนมัติต้องระบุงาน เช่น ดำเนินการต่อ แก้ไฟล์ run.py ..."})

    client = _get_groq_client(groq_client)
    if isinstance(client, Exception):
        return _result_for_run({"ok": False, "error": f"เชื่อมต่อ AI ไม่ได้: {client}"})

    proposal_result = developer_mode.handle(remainder, groq_client=client)
    if not proposal_result.get("ok"):
        return _result_for_run(proposal_result)

    proposal_id = proposal_result.get("proposal_id")
    if not proposal_id:
        return _result_for_run({"ok": False, "error": "AI สร้างผลลัพธ์แล้วแต่ไม่มี proposal id"})

    approved = developer_mode.approve(proposal_id)
    return _result_for_run(approved)


def execute_developer_command(text: str, root=".", groq_client=None):
    normalized = (text or "").lower().strip()

    if normalized in ("สถานะระบบ", "/status", "status"):
        status = developer_mode.system_status()
        summary = (
            "🤖 Jarvis: ONLINE\n"
            f"🛠 Developer Mode: {status['developer_mode'].upper()}\n"
            f"🌿 Branch: {status['branch']}\n"
            f"🧠 Model: {status['model']}\n"
            f"📦 Max file: {status['max_file_chars']} chars\n"
            f"⏳ Pending: {status['pending_proposal'] or 'none'}"
        )
        return {"files": [{"status": "ok", "file": summary, "lines": 1}]}

    if normalized in ("ทดสอบ rollback", "ทดสอบโรลแบ็ก", "test rollback", "/rollback", "/rollback-test"):
        return _result_for_run(developer_mode.self_test_rollback())

    if "rollback" in normalized or "โรลแบ็ก" in normalized:
        return _result_for_run(developer_mode.self_test_rollback())

    if normalized.startswith("ดำเนินการต่อ") or normalized.startswith("ดำเนินการ"):
        return _execute_auto(text, groq_client=groq_client)

    match = re.search(r"อนุมัติ\s+([a-f0-9]{10})", normalized)
    if match:
        return _result_for_run(developer_mode.approve(match.group(1)))

    match = re.search(r"(?:ยกเลิก patch|ยกเลิกแพตช์)\s+([a-f0-9]{10})", normalized)
    if match:
        return _result_for_run(developer_mode.reject(match.group(1)))

    if any(k in normalized for k in _PROJECT_COMMANDS):
        return handle_dev_request(text, root)

    client = _get_groq_client(groq_client)
    if isinstance(client, Exception):
        return _result_for_run({"ok": False, "error": f"เชื่อมต่อ AI ไม่ได้: {client}"})

    return _result_for_run(developer_mode.handle(text, groq_client=client))
