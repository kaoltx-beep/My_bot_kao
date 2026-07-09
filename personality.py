import json
import os

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
"""
}


def load_mode():
    if os.path.exists(MODE_FILE):
        try:
            with open(MODE_FILE,"r",encoding="utf-8") as f:
                data=json.load(f)
                if data.get("mode") in MODES:
                    return data["mode"]
        except:
            pass
    return "NORMAL"

CURRENT_MODE = load_mode()


def set_mode(mode):
    global CURRENT_MODE
    if mode in MODES:
        CURRENT_MODE = mode
        with open(MODE_FILE,"w",encoding="utf-8") as f:
            json.dump({"mode":mode},f,ensure_ascii=False)
        return True
    return False


def get_mode():
    return CURRENT_MODE


def get_prompt():
    return MODES["NORMAL"]
