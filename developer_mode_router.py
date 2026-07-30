"""Jarvis Developer Mode router: analyze, propose, approve, apply."""

from dev_agent import analyze
from dev_handler import handle_dev_request
from dev_patcher import apply_plan
from dev_session import clear_pending, get_pending, set_pending

_PATCH_REQUEST_WORDS = ("สร้าง patch", "ช่วยแก้โค้ด", "แก้โค้ด", "สร้างโค้ด")
_ANALYZE_WORDS = ("วิเคราะห์โปรเจกต์", "ตรวจโปรเจกต์", "scan โปรเจกต์", "ตรวจ error", "วิเคราะห์โค้ด")


def is_developer_command(text):
    text = (text or "").lower()
    keywords = _PATCH_REQUEST_WORDS + _ANALYZE_WORDS + ("ดำเนินการ", "ยกเลิก patch", "ยกเลิก")
    return any(keyword in text for keyword in keywords)


def _result(message):
    # run.py already formats Developer Mode through result["files"].
    # Keep the complete preview in one item so no core bot file needs editing.
    message = str(message)
    if len(message) > 3600:
        message = message[:3600] + "\n…(ตัด preview)"
    return {
        "mode": "developer",
        "files": [{"status": "ok", "file": message, "lines": 0, "errors": []}],
    }


def _preview(plan):
    target = plan.get("target_file", "unknown")
    action = plan.get("action", "add_function")
    description = plan.get("description", "")
    code = plan.get("new_code", "")
    return (
        "🛠 Developer Mode\n"
        "📋 Patch Proposal\n"
        f"ไฟล์: {target}\n"
        f"การทำงาน: {action}\n"
        f"รายละเอียด: {description}\n\n"
        "โค้ดที่จะเพิ่ม:\n"
        f"{code}\n\n"
        "✅ ตรวจ syntax ของโค้ดใหม่แล้ว\n"
        "พิมพ์ 'ดำเนินการ' เพื่อ Backup → Apply → Syntax Check\n"
        "พิมพ์ 'ยกเลิก' เพื่อทิ้ง patch"
    )


def execute_developer_command(text, root="."):
    text = (text or "").strip()
    normalized = text.lower()

    if "ยกเลิก" in normalized:
        had_pending = get_pending() is not None
        clear_pending()
        return _result("🛠 Developer Mode\nยกเลิก patch แล้วครับ" if had_pending else "🛠 Developer Mode\nไม่มี patch ที่รออนุมัติครับ")

    if "ดำเนินการ" in normalized:
        plan = get_pending()
        if plan is None:
            return _result("🛠 Developer Mode\nไม่มี patch ที่รออนุมัติครับ")
        result = apply_plan(plan)
        clear_pending()
        return _result("🛠 Developer Mode\n" + result)

    if any(word in normalized for word in _PATCH_REQUEST_WORDS):
        plan = analyze(text)
        if plan.get("error"):
            return _result("🛠 Developer Mode\n" + str(plan["error"]))
        set_pending(plan)
        return _result(_preview(plan))

    if any(word in normalized for word in _ANALYZE_WORDS):
        return handle_dev_request(text, root)

    return _result("🛠 Developer Mode\nไม่เข้าใจคำสั่ง Developer Mode นี้ครับ")
