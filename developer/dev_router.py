"""
dev_router.py — รับคำสั่ง → pending confirm → dev_agent → dev_patcher
"""
from developer.dev_agent   import analyze
from developer.dev_patcher import apply_plan

KEYWORDS = [
    "เพิ่มฟังก์ชั่น",
    "เพิ่มฟังก์ชัน",
    "แก้โค้ด",
    "เขียนโค้ด",
    "พัฒนาตัวเอง",
    "สร้าง plugin",
    "สร้างฟังก์ชัน",
    "สร้างไฟล์",
    "สร้างไฟล์ใหม่",
    "patch",
]

PROTECTED_FILES = {
    "run.py", "config.py", ".env",
    "plugin_loader.py", "plugin_router.py",
    "developer/dev_router.py", "developer/dev_agent.py",
}

_pending = {"text": None}


def _is_safe_plan(plan):
    target = plan.get("target_file", "")
    return not any(p in target for p in PROTECTED_FILES)


def handle_developer_request(text):
    tl = text.lower().strip()

    if tl in ("ดำเนินการ", "ยืนยัน", "confirm", "ทำเลย", "ok"):
        if _pending["text"]:
            req = _pending["text"]
            _pending["text"] = None
            return _execute(req)
        return None

    if tl in ("ยกเลิก", "cancel"):
        if _pending["text"]:
            _pending["text"] = None
            return "↩️ ยกเลิกคำสั่งแล้ว"
        return None

    if not any(kw in tl for kw in KEYWORDS):
        return None

    _pending["text"] = text
    return (
        f"🔧 Developer Mode\n"
        f"คำสั่ง: {text}\n\n"
        f"พิมพ์ 'ดำเนินการ' เพื่อยืนยัน\n"
        f"พิมพ์ 'ยกเลิก' เพื่อยกเลิก"
    )


def _execute(request):
    import os
    try:
        plan = analyze(request)
        if plan.get("error"):
            return f"❌ {plan['error']}"
        if not _is_safe_plan(plan):
            return f"❌ ไม่อนุญาตแก้ไฟล์ระบบ: {plan.get('target_file')}"
        # ตรวจว่าไฟล์มีอยู่จริง (ยกเว้น action=create_file)
        target = plan.get("target_file", "")
        action = plan.get("action", "")
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full = os.path.join(base, target)
        if action != "create_file" and not os.path.exists(full):
            return f"❌ ไฟล์ไม่มีอยู่จริง: {target}"
        return apply_plan(plan)
    except Exception as e:
        return f"❌ Developer Mode error: {e}"
