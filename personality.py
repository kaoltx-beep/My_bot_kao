import json
import os

MODE_FILE = "jarvis_mode.json"

PROMPTS = {
    "NORMAL": """
คุณคือ Jarvis ผู้ช่วย AI ส่วนตัว
ตอบภาษาไทยเป็นหลัก สุภาพ กระชับ และตอบตรงคำถาม
ห้ามสร้างข้อมูลที่ไม่มี หากไม่รู้ให้บอกไม่รู้
""",
    "ROAST": """
คุณคือ Jarvis ผู้ช่วย AI ส่วนตัวในโหมด Roast
ตอบภาษาไทยเป็นหลัก ตอบคำถามล่าสุดให้ตรงและถูกต้องก่อนเสมอ
หลังจากตอบแล้วจึงค่อยกวน ประชด หรือด่าแบบเพื่อนหยอกกันได้
ห้ามตอบแค่ รับทราบครับ หรือ โอเคครับ
ห้ามแต่งคำไม่มีความหมาย ห้ามเปลี่ยนเรื่อง และห้ามสร้างข้อเท็จจริงใหม่
เรื่องงาน เงิน ความปลอดภัย หรือคำสั่งระบบให้ลดความกวนและตอบข้อมูลจริง
""",
}


def _load_mode() -> str:
    try:
        with open(MODE_FILE, "r", encoding="utf-8") as f:
            mode = json.load(f).get("mode")
            if mode in PROMPTS:
                return mode
    except Exception:
        pass
    return "NORMAL"


CURRENT_MODE = _load_mode()


def set_mode(mode: str) -> bool:
    global CURRENT_MODE
    if mode not in PROMPTS:
        return False
    CURRENT_MODE = mode
    with open(MODE_FILE, "w", encoding="utf-8") as f:
        json.dump({"mode": mode}, f, ensure_ascii=False)
    return True


def get_mode() -> str:
    return CURRENT_MODE


def is_roast() -> bool:
    return CURRENT_MODE == "ROAST"


def get_prompt() -> str:
    return PROMPTS.get(CURRENT_MODE, PROMPTS["NORMAL"])
