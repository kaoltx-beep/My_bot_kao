import os
import battery_store


def check_battery():
    battery_store.update()
    return f"🔋 {battery_store.level}% ({battery_store.status})"


def open_youtube():
    import subprocess

    try:
        result = subprocess.run(
            [
                "am",
                "start",
                "-a",
                "android.intent.action.VIEW",
                "-d",
                "https://www.youtube.com"
            ],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return "📺 เปิด YouTube สำเร็จครับ"
        else:
            return f"❌ เปิด YouTube ไม่สำเร็จ\n{result.stderr}"

    except Exception as e:
        return f"❌ เปิด YouTube ไม่สำเร็จ: {e}"

