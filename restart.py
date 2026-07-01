import os
import sys
import time

while True:
    print("🚀 Jarvis กำลังเริ่มทำงาน...")
    # ใช้ sys.executable เพื่อให้แอป Pydroid 3 เรียกคำสั่งรันได้ถูกต้อง
    os.system(f"{sys.executable} run.py") 
    print("❌ บอทดับ! กำลังเปิดใหม่อัตโนมัติใน 3 วินาที...")
    time.sleep(3)
