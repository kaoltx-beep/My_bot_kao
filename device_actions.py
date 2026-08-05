<<<<<<< HEAD
import requests
import battery_store
import config


def check_battery():
    battery_store.update()
    return f"🔋 {battery_store.level}% ({battery_store.status})"


def open_youtube():
    try:
        url = config.MACRODROID_WEBHOOK_URL

        if not url:
            return "❌ ไม่พบ MacroDroid webhook"

        response = requests.get(
            url,
            timeout=10
        )

        if response.status_code == 200:
            return "📺 ส่งคำสั่งเปิด YouTube ให้ MacroDroid แล้วครับ"
        else:
            return f"❌ MacroDroid ตอบกลับ {response.status_code}"

    except Exception as e:
        return f"❌ เปิด YouTube ไม่สำเร็จ: {e}"
=======
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
>>>>>>> ef0ef12 (add pulse system)
