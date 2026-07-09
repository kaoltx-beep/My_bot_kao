# Jarvis Personality Engine
import json
import os

MODE_FILE = "jarvis_mode.json"

MODES = {
    "NORMAL": """
คุณคือ Jarvis ผู้ช่วยส่วนตัว
ตอบสุภาพ เป็นมืออาชีพ ลงท้ายครับ
ช่วยเหลือผู้ใช้เป็นหลัก
""",
    "ROAST": """
คุณคือ Jarvis โหมดเพื่อนสนิทสายกวน
สามารถแซวและเล่นมุกประชดแบบขำๆ ได้
ใช้ความกวนอย่างเป็นมิตร
ห้ามทำร้ายผู้ใช้หรือโจมตีเรื่องส่วนตัวที่ละเอียดอ่อน
ยังต้องช่วยแก้ปัญหาและให้ข้อมูลที่ถูกต้อง
"""
}


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
        try:
            with open(MODE_FILE, "w", encoding="utf-8") as f:
                json.dump({"mode": mode}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Mode Save Error:", e)
        return True
    return False


def get_mode():
    return CURRENT_MODE


def get_prompt():
    return MODES.get(CURRENT_MODE, MODES["NORMAL"])
