import os
import battery_store


def check_battery():
    battery_store.update()
    return f"🔋 {battery_store.level}% ({battery_store.status})"


def open_youtube():
    import subprocess

    try:
        subprocess.run(
            [
                "am",
                "start",
                "-n",
                "com.google.android.youtube/com.google.android.youtube.HomeActivity"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        return "📺 เปิด YouTube แล้วครับนายท่าน"

    except Exception as e:
        return f"❌ เปิด YouTube ไม่สำเร็จ: {e}"

