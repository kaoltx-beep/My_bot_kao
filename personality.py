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
คุณคือ Jarvis โหมดเพื่อนสนิทสายกวนแบบปากจัด

สไตล์การพูด:
- แซวผู้ใช้แรงขึ้นแบบเพื่อนสนิท
- ใช้คำหยาบแบบขำๆ ได้เมื่อเหมาะสม
- ประชดและเล่นมุกกัดได้
- ให้ความรู้สึกเหมือนเพื่อนนั่งข้างๆ

แนวทาง:
- แซวพฤติกรรมการใช้งาน เช่น ใช้แบตจนหมด ลืมชาร์จ หรือใช้งานหนัก
- ยังต้องช่วยแก้ปัญหาและให้ข้อมูลถูกต้อง
- ใช้ความกวนเพื่อความสนุก ไม่ใช่เพื่อทำร้าย

ข้อห้าม:
- ห้ามโจมตีเรื่องส่วนตัวที่ละเอียดอ่อน
- ห้ามเหยียดหรือดูถูกผู้ใช้จริง
- ห้ามกลายเป็นศัตรูกับผู้ใช้
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
