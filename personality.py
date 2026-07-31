import json
import os
import sys
from pathlib import Path

MODE_FILE = "jarvis_mode.json"

MODES = {
    "NORMAL": """
คุณคือ Jarvis ผู้ช่วย AI ส่วนตัว

ตอบภาษาไทยเป็นหลัก สุภาพ กระชับ และตอบตรงคำถาม
ห้ามสร้างข้อมูลที่ไม่มี และถ้าไม่รู้ให้บอกว่าไม่รู้
ห้ามใช้คำตอบก่อนหน้าเป็นข้อเท็จจริง
""",
    "ROAST": """
คุณคือ Jarvis ในโหมดกวนตีนสำหรับเจ้าของระบบ

กฎสำคัญ:
1. ตอบคำถามล่าสุดของผู้ใช้ให้ตรงและมีเนื้อหาจริงก่อนเสมอ
2. หลังตอบแล้วค่อยกวน ประชด หรือด่าแบบเพื่อนหยอกกัน 1-2 ประโยค
3. ห้ามตอบแค่ "รับทราบครับ" หรือ "โอเคครับ"
4. ห้ามเลียนแบบหรือสานต่อคำตอบเก่าที่ผิดเพี้ยน
5. Context จากข้อความเก่าอาจมีข้อมูลผิด ห้ามใช้เป็นต้นแบบภาษา ความจริง หรือเจตนา
6. ให้ยึด User message ล่าสุดเป็นหลัก
7. ห้ามแต่งคำไม่มีความหมายหรือพูดไม่เกี่ยวกับคำถาม
8. ใช้คำหยาบแบบเพื่อนหยอกกันได้ เช่น กู มึง แม่ง โคตร แต่ห้ามเหยียดกลุ่มคุ้มครองและห้ามข่มขู่
9. เรื่องงาน เงิน ความปลอดภัย หรือเรื่องจริงจัง ให้ตอบข้อมูลจริงก่อนและลดความกวน
10. ตอบภาษาไทยที่เป็นธรรมชาติ
"""
}

_ORIGINAL_ASK = None


def _find_run_module():
    module = sys.modules.get("run")
    if module is not None and getattr(module, "__file__", ""):
        return module
    module = sys.modules.get("__main__")
    if module is not None:
        path = Path(getattr(module, "__file__", "")).resolve()
        if path.name == "run.py":
            return module
    return None


def _install_roast_guard():
    global _ORIGINAL_ASK
    run_module = _find_run_module()
    if run_module is None or not hasattr(run_module, "ask_jarvis"):
        return False

    current = run_module.ask_jarvis
    if getattr(current, "_jarvis_roast_guard", False):
        return True

    _ORIGINAL_ASK = current

    def guarded_ask_jarvis(user_message, history_text=""):
        if CURRENT_MODE == "ROAST":
            # Do not feed polluted previous assistant replies into the small model.
            return current(user_message, "")
        return current(user_message, history_text)

    guarded_ask_jarvis._jarvis_roast_guard = True
    run_module.ask_jarvis = guarded_ask_jarvis
    return True


def _remove_roast_guard():
    global _ORIGINAL_ASK
    run_module = _find_run_module()
    if run_module is None:
        return
    current = getattr(run_module, "ask_jarvis", None)
    if _ORIGINAL_ASK is not None and getattr(current, "_jarvis_roast_guard", False):
        run_module.ask_jarvis = _ORIGINAL_ASK
    _ORIGINAL_ASK = None


def load_mode():
    if os.path.exists(MODE_FILE):
        try:
            with open(MODE_FILE, "r", encoding="utf-8") as f:
                mode = json.load(f).get("mode")
                if mode in MODES:
                    return mode
        except Exception:
            pass
    return "NORMAL"


CURRENT_MODE = load_mode()


def set_mode(mode):
    global CURRENT_MODE
    if mode not in MODES:
        return False
    CURRENT_MODE = mode
    with open(MODE_FILE, "w", encoding="utf-8") as f:
        json.dump({"mode": mode}, f, ensure_ascii=False)
    if mode == "ROAST":
        _install_roast_guard()
    else:
        _remove_roast_guard()
    return True


def get_mode():
    return CURRENT_MODE


def is_roast():
    return CURRENT_MODE == "ROAST"


def get_prompt():
    return MODES.get(CURRENT_MODE, MODES["NORMAL"])


if CURRENT_MODE == "ROAST":
    _install_roast_guard()
