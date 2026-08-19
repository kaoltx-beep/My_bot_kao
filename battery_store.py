import json
import subprocess

level = 0
status = "unknown"


def update():
    global level, status

    # Method 1: Termux API
    try:
        raw = subprocess.check_output(["termux-battery-status"], text=True)
        data = json.loads(raw)

        level = data.get("percentage", 0)
        status = "charging" if data.get("status") == "CHARGING" else "discharging"
        return
    except Exception:
        pass

    # Method 2: Android dumpsys fallback
    try:
        raw = subprocess.check_output(["sh", "-c", "dumpsys battery"], text=True)

        for line in raw.splitlines():
            if "level:" in line:
                level = int(line.split(":", 1)[1].strip())
            if "status:" in line:
                status = "charging" if line.split(":", 1)[1].strip() == "2" else "discharging"
        return
    except Exception:
        level = -1
        status = "error"
