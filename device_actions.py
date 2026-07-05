import os
import battery_store


def check_battery():
    battery_store.update()
    return f"🔋 {battery_store.level}% ({battery_store.status})"


def open_youtube():
    os.system("termux-open https://youtube.com")
    return "📺 เปิด YouTube แล้ว"