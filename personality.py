import json
import os
import sys

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

_CURRENT_ORIGINAL_ASK = None


def _install_roast_wrapper():
    """Install a deterministic roast filter around run.ask_jarvis after run is loaded."""
    global _CURRENT_ORIGINAL_ASK
    run_module = sys.modules.get("run")
    if run_module is None or not hasattr(run_module, "ask_jarvis"):
        return
    current = run_module.ask_jarvis
    if getattr(current, "_jarvis_roast_wrapper", False):
        return
    _CURRENT_ORIGINAL_ASK = current

    from roast_rules import reply as deterministic_roast_reply

    def wrapped_ask_jarvis(user_message, history_text=""):
        if CURRENT_MODE == "ROAST":
            fixed = deterministic_roast_reply(user_message)
            if fixed:
                return {"reply": fixed, "action": None}
        return current(user_message, history_text)

    wrapped_ask_jarvis._jarvis_roast_wrapper = True
    run_module.ask_jarvis = wrapped_ask_jarvis


def _remove_roast_wrapper():
    global _CURRENT_ORIGINAL_ASK
    run_module = sys.modules.get("run")
    if run_module is None:
        return
    if _CURRENT_ORIGINAL_ASK is not None and getattr(run_module.ask_jarvis, "_jarvis_roast_wrapper", False):
        run_module.ask_jarvis = _CURRENT_ORIGINAL_ASK
    _CURRENT_ORIGINAL_ASK = None


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
            _install_roast_wrapper()
        else:
            _remove_roast_wrapper()
        return True
    return False


def get_mode():
    return CURRENT_MODE


def get_prompt():
    return MODES.get(CURRENT_MODE, MODES["NORMAL"])
