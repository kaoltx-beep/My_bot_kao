import json
import os
import sys
from pathlib import Path

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
- คำถามทั่วไปต้องมีคำตอบจริง ห้ามตอบแค่ "รับทราบครับ" หรือ "โอเคครับ"
- ถ้าคำถามกำกวม ให้ถามกลับสั้นๆ แทนการเดา
- กวน ประชด จิกกัด และด่าได้แรงพอสมควรในเชิงหยอกล้อ
- ใช้คำหยาบได้เมื่อเข้ากับบริบท เช่น กู มึง แม่ง โคตร บ้า ชิบหาย แต่ต้องไม่เหยียดกลุ่มคุ้มครองใดๆ
- เน้นด่าความคิด การตัดสินใจ ความซุ่มซ่าม หรือสถานการณ์ ไม่ใช่คุณค่าความเป็นมนุษย์
- ห้ามข่มขู่หรือชวนทำร้ายใคร
- ห้ามสร้างข้อมูลเท็จ
- ห้ามแต่งคำไม่มีความหมาย
- ถ้าเรื่องจริงจังหรืออันตราย ให้ลดความกวนและตอบจริงจัง
"""
}

_ORIGINAL_ASK = None


def _find_run_module():
    """Find the live run.py module whether Python named it run or __main__."""
    module = sys.modules.get("run")
    if module is not None and getattr(module, "__file__", ""):
        return module

    module = sys.modules.get("__main__")
    if module is not None:
        path = Path(getattr(module, "__file__", "")).resolve()
        if path.name == "run.py":
            return module
    return None


def _install_roast_ask_guard():
    global _ORIGINAL_ASK
    run_module = _find_run_module()
    if run_module is None or not hasattr(run_module, "ask_jarvis"):
        return False

    current = run_module.ask_jarvis
    if getattr(current, "_jarvis_roast_ask_guard", False):
        return True

    _ORIGINAL_ASK = current
    from roast_rules import reply as roast_reply

    def guarded_ask_jarvis(user_message, history_text=""):
        if CURRENT_MODE == "ROAST":
            fixed = roast_reply(user_message)
            if fixed:
                return {"reply": fixed, "action": None}
        return current(user_message, history_text)

    guarded_ask_jarvis._jarvis_roast_ask_guard = True
    run_module.ask_jarvis = guarded_ask_jarvis
    return True


def _remove_roast_ask_guard():
    global _ORIGINAL_ASK
    run_module = _find_run_module()
    if run_module is None:
        return
    current = getattr(run_module, "ask_jarvis", None)
    if _ORIGINAL_ASK is not None and getattr(current, "_jarvis_roast_ask_guard", False):
        run_module.ask_jarvis = _ORIGINAL_ASK
    _ORIGINAL_ASK = None


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
            _install_roast_ask_guard()
        else:
            _remove_roast_ask_guard()
        return True
    return False


def get_mode():
    return CURRENT_MODE


def get_prompt():
    return MODES.get(CURRENT_MODE, MODES["NORMAL"])


if CURRENT_MODE == "ROAST":
    _install_roast_ask_guard()
