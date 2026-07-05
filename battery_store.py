import subprocess
import json

level = 0
status = "unknown"

def update():
    global level, status

    try:
        raw = subprocess.check_output(["termux-battery-status"], text=True)
        data = json.loads(raw)

        level = data.get("percentage", 0)

        if data.get("status") == "CHARGING":
            status = "charging"
        else:
            status = "discharging"

    except Exception as e:
        level = -1
        status = f"error"