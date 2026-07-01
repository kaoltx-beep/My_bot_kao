from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class IntentEnum(str, Enum):
    CHAT = "chat"
    CONTROL = "control"
    MEMORY = "memory"
    SEARCH = "search"
    DEV = "dev_command"
    SYSTEM = "system"
    UNKNOWN = "unknown"

class IntentResult(BaseModel):
    intents: List[IntentEnum]
    confidence: float
    metadata: Optional[Dict[str, Any]] = {}

def classify_intent(user_text: str) -> IntentResult:
    system_prompt = """
    วิเคราะห์ข้อความของผู้ใช้ แล้วตอบกลับเป็น JSON ตาม Schema ที่กำหนดเท่านั้น
    
    หมวดหมู่ (Intents):
    - 'chat': คุยเล่น, ถามตอบทั่วไป
    - 'control': สั่งเปิด/ปิดอุปกรณ์, ควบคุมระบบ
    - 'memory': สั่งให้จำ, ค้นหาความทรงจำเก่า
    - 'search': สั่งค้นหาข้อมูลภายนอก เช่น Google, YouTube
    - 'dev_command': สั่งเขียนโค้ด, อธิบายโค้ด, แก้ไขไฟล์โปรเจกต์
    - 'system': สั่งเช็กสถานะเซิร์ฟเวอร์, รีบูตระบบ
    - 'unknown': ไม่มั่นใจ หรือไม่เข้าพวกใดๆ
    
    ให้ดึงข้อมูลสำคัญใส่ใน metadata ด้วย (ถ้ามี) เช่น:
    - ถ้าเป็น search ให้ใส่ {"query": "หัวข้อที่ค้นหา"}
    - ถ้าเป็น dev_command ให้ใส่ {"file_name": "ชื่อไฟล์ (ถ้ามี)", "action": "สิ่งที่ให้ทำกับโค้ด"}
    """
    pass
