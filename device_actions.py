import battery_store

def check_battery() -> str:
    """ฟังก์ชันเช็คแบตเตอรี่สำหรับ Jarvis v5"""
    return f"ระดับแบตเตอรี่ปัจจุบันของเครื่องคือ {battery_store.latest_battery}"

def open_youtube() -> str:
    """ฟังก์ชันเปิดยูทูปสำหรับ Jarvis v5 (คุณสามารถใส่โค้ดสั่งเปิดจริงเพิ่มตรงนี้ได้)"""
    return "กำลังเปิดแอปพลิเคชัน YouTube ให้คุณชั่วครู่ครับ"


def execute_device_action(action_text: str) -> str | None:
    """ฟังก์ชันเดิม (Legacy) เพื่อรองรับระบบเก่าและกันระบบอื่นพัง"""
    if not action_text:
        return None
        
    if "เช็คแบต" in action_text or "check_battery" in action_text:
        return check_battery()
        
    if "เปิดยูทูป" in action_text or "open_youtube" in action_text:
        return open_youtube()
        
    return None