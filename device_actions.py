import requests
import battery_store
import config


def check_battery() -> str:
    battery_store.update()
    return f"🔋 {battery_store.level}% ({battery_store.status})"


def open_youtube() -> str:
    try:
        url = config.MACRODROID_WEBHOOK_URL
        if not url:
            return "❌ ไม่พบ MacroDroid webhook"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return "📺 ส่งคำสั่งเปิด YouTube ให้ MacroDroid แล้วครับ"
        return f"❌ MacroDroid ตอบกลับ {response.status_code}"
    except Exception as e:
        return f"❌ เปิด YouTube ไม่สำเร็จ: {e}"


def execute_device_action(action_text: str) -> str | None:
    if not action_text:
        return None
    if "เช็คแบต" in action_text or "check_battery" in action_text:
        return check_battery()
    if "เปิดยูทูป" in action_text or "open_youtube" in action_text:
        return open_youtube()
    return None
