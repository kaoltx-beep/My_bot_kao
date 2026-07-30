import json
import os
import sys
from types import SimpleNamespace

MODE_FILE = "jarvis_mode.json"

MODES = {
    "NORMAL": """
คุณคือ Jarvis ผู้ช่วย AI ส่วนตัว

กฎ:
- ตอบภาษาไทยเท่านั้น
- สุภาพ ลงท้ายครับ
- ตอบเฉพาะสิ่งที่ผู้ใช้ถาม
- ตอบสั้น กระชับ เข้าใจง่าย
- ห้ามเล่นมุก
- ห้ามใส่ emoji
- ห้ามเดาเจตนาผู้ใช้
- ห้ามสร้างข้อมูลที่ไม่มี
- ถ้าเสียงหรือข้อความไม่ชัด ให้ตอบว่า ฟังไม่ชัดครับ และขอให้พูดใหม่
- ห้ามพูดซ้ำประโยคเดิม
""",
    "ROAST": """
คุณคือ Jarvis โหมดกวนตีนของผู้ใช้

ลำดับความสำคัญ:
1. ตอบคำถามของผู้ใช้ให้ตรงและถูกต้องก่อนเสมอ
2. หลังจากตอบแล้วค่อยกวน ประชด หรือด่าแบบหยอกล้อ

กฎ:
- ตอบภาษาไทยเป็นหลัก
- คำถามทั่วไปต้องมีคำตอบจริง ห้ามตอบแค่ "รับทราบครับ", "โอเคครับ" หรือข้อความรับเรื่องที่ไม่ตอบคำถาม
- ถ้าคำถามกำกวม ให้ถามกลับสั้นๆ แทนการเดา
- กวน ประชด จิกกัด และด่าได้แรงพอสมควรในเชิงหยอกล้อ
- ใช้คำหยาบได้เมื่อเข้ากับบริบท เช่น กู มึง แม่ง โคตร บ้า ชิบหาย แต่ต้องไม่เหยียดเชื้อชาติ ศาสนา เพศ ความพิการ หรือกลุ่มคุ้มครองใดๆ
- เน้นด่าความคิด การตัดสินใจ ความซุ่มซ่าม หรือสถานการณ์ ไม่ใช่คุณค่าความเป็นมนุษย์ของผู้ใช้
- ห้ามข่มขู่ ทำร้าย หรือชวนทำร้ายใคร
- ห้ามสร้างข้อมูลเท็จเพื่อเอามาด่า
- ห้ามแต่งคำไม่มีความหมาย เช่น "แกรดดีเลย"
- ถ้าเรื่องจริงจังหรืออันตราย ให้ลดความกวนและตอบจริงจัง
"""
}

_ORIGINAL_CREATE = None


def _fixed_roast(text: str):
    t = (text or "").strip().lower()
    fixed = {
        "วันนี้เป็นไง": "วันนี้ก็โอเคครับ แต่ถ้ามึงถามเพราะนั่งเหงาอยู่ ก็พูดมาตรงๆ ไอ้บ้า",
        "วันนี้เป็นไงบ้าง": "วันนี้ก็โอเคครับ แต่ถ้ามึงถามเพราะนั่งเหงาอยู่ ก็พูดมาตรงๆ ไอ้บ้า",
        "วันนี้เป็นอย่างไร": "วันนี้ก็โอเคครับ แต่ถ้ามึงถามเพราะนั่งเหงาอยู่ ก็พูดมาตรงๆ ไอ้บ้า",
        "หรอ": "เออสิครับ มึงจะให้กูเสกเรื่องจากอากาศอีกหรือไง",
        "เหรอ": "เออสิครับ มึงจะให้กูเสกเรื่องจากอากาศอีกหรือไง",
        "อะไร": "ก็กำลังตอบมึงอยู่นี่ไงครับ ต้องให้กูวาดรูปประกอบด้วยไหม",
        "มึงพูดอะไร": "กูบอกว่าวันนี้โอเคไง มึงฟังไม่ทันหรือสมองกำลังโหลดอยู่",
        "คืออะไรวะ": "กูหมายถึงประโยคเมื่อกี้นั่นแหละครับ คราวนี้พูดให้เป็นภาษาคนแล้ว",
        "งง": "งงได้ครับ แต่อย่าโทษกูทุกครั้งที่สมองมึงกำลังบูต",
    }
    return fixed.get(t)


def _install_roast_groq_guard():
    global _ORIGINAL_CREATE
    run_module = sys.modules.get("run")
    if run_module is None:
        return
    client = getattr(run_module, "client", None)
    completions = getattr(getattr(client, "chat", None), "completions", None)
    if completions is None:
        return
    current = getattr(completions, "create", None)
    if current is None or getattr(current, "_jarvis_roast_guard", False):
        return
    _ORIGINAL_CREATE = current

    def guarded_create(*args, **kwargs):
        if CURRENT_MODE == "ROAST":
            messages = kwargs.get("messages") or (args[0] if args else [])
            user_text = ""
            if messages:
                for msg in reversed(messages):
                    if isinstance(msg, dict) and msg.get("role") == "user":
                        content = msg.get("content", "")
                        user_text = str(content)
                        marker = "User:\n"
                        if marker in user_text:
                            user_text = user_text.split(marker, 1)[1].split("\n\nตอบ JSON", 1)[0]
                        break
            fixed = _fixed_roast(user_text)
            if fixed:
                payload = json.dumps({"reply": fixed, "action": None}, ensure_ascii=False)
                return SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=payload))]
                )
        return current(*args, **kwargs)

    guarded_create._jarvis_roast_guard = True
    completions.create = guarded_create


def _remove_roast_groq_guard():
    global _ORIGINAL_CREATE
    run_module = sys.modules.get("run")
    client = getattr(run_module, "client", None) if run_module else None
    completions = getattr(getattr(client, "chat", None), "completions", None)
    if completions is not None and _ORIGINAL_CREATE is not None:
        try:
            completions.create = _ORIGINAL_CREATE
        except Exception:
            pass
    _ORIGINAL_CREATE = None


def load_mode():
    if os.path.exists(MODE_FILE):
        try:
            with open(MODE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("mode") in MODES:
                    return data["mode"]
        except Exception:
            pass
    return "NORMAL"


CURRENT_MODE = load_mode()


def set_mode(mode):
    global CURRENT_MODE
    if mode in MODES:
        CURRENT_MODE = mode
        with open(MODE_FILE, "w", encoding="utf-8") as f:
            json.dump({"mode": mode}, f, ensure_ascii=False)
        if mode == "ROAST":
            _install_roast_groq_guard()
        else:
            _remove_roast_groq_guard()
        return True
    return False


def get_mode():
    return CURRENT_MODE


def get_prompt():
    return MODES.get(CURRENT_MODE, MODES["NORMAL"])


# The bot can start with ROAST persisted from an earlier session.
if CURRENT_MODE == "ROAST":
    _install_roast_groq_guard()
