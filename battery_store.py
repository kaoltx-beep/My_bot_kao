import subprocess
import json

level = 0
<<<<<<< HEAD
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
                level = int(line.split(":")[1].strip())

            if "status:" in line:
                status = "charging" if "2" in line else "discharging"

        return

    except Exception:
        level = -1
        status = "error"
=======
status = "กำลังตรวจสอบ"

def update():
    global level, status
    try:
        # ดึงค่าสถานะแบตเตอรี่จริงจาก Android
        result = subprocess.check_output(["termux-battery-status"], text=True)
        data = json.loads(result)
        
        level = data.get("percentage", 0)
        raw_status = data.get("status")

        if raw_status == "CHARGING":
            status = "กำลังชาร์จ ⚡"
        else:
            status = "ไม่ได้ชาร์จ 🔋"

        # แจ้งเตือนหากแบตเตอรี่ต่ำ
        if level <= 20:
            status += " ⚠️ (แบตเตอรี่ต่ำกว่า 20%)"
            
    except Exception:
        status = "ไม่สามารถดึงข้อมูลระบบได้"


>>>>>>> ef0ef12 (add pulse system)
