# Jarvis Personality Engine

CURRENT_MODE = "NORMAL"

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


def set_mode(mode):
    global CURRENT_MODE
    if mode in MODES:
        CURRENT_MODE = mode
        return True
    return False


def get_mode():
    return CURRENT_MODE


def get_prompt():
    return MODES.get(CURRENT_MODE, MODES["NORMAL"])
