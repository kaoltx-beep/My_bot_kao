import subprocess
import json

level = 0
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


