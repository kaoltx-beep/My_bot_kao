import os
import battery_store


def check_battery():
    battery_store.update()
    return f"🔋 {battery_store.level}% ({battery_store.status})"


def open_youtube():
    try:
        result = os.system(
            "am start -a android.intent.action.VIEW -d https://www.youtube.com"
        )

        if result == 0:
            return "📺 เปิด YouTube แล้วครับนายท่าน"

        return "❌ เปิด YouTube ไม่สำเร็จ"

    except Exception as e:
        return f"❌ เปิด YouTube ไม่สำเร็จ: {e}"
