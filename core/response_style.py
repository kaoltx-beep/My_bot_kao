from __future__ import annotations

import re


ROAST_STYLE_PROMPT = """
คุณเป็นตัวแปลงสไตล์ข้อความของ Jarvis

หน้าที่ของคุณคือเอา BASE ANSWER ที่ถูกต้องอยู่แล้วมาเปลี่ยนน้ำเสียงให้เป็น Roast แบบเพื่อนหยอกกัน

กฎเด็ดขาด:
- ห้ามเปลี่ยนข้อเท็จจริง
- ห้ามเพิ่มข้อมูลใหม่
- ห้ามเปลี่ยนความหมายของ BASE ANSWER
- ห้ามตอบคนละเรื่อง
- ตอบภาษาไทยธรรมชาติ
- กวน ประชด จิกกัด หรือใช้ กู/มึง/แม่ง ได้ตามบริบท
- ห้ามแต่งคำไม่มีความหมาย
- ห้ามตอบแค่ รับทราบครับ หรือ โอเคครับ
- ถ้า BASE ANSWER สั้น ให้คงสาระเดิมแล้วเติมมุกสั้นๆ เท่านั้น
- คืน JSON เท่านั้น: {"reply": "..."}
"""


def normalize_reply(value: object) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def valid_base_reply(reply: str) -> bool:
    text = normalize_reply(reply)
    if not text:
        return False
    if len(text) > 2500:
        return False
    if text in {"รับทราบครับ", "โอเคครับ", "รับทราบ", "โอเค"}:
        return False
    return True


def valid_roast_reply(user_message: str, base_reply: str, roast_reply: str) -> bool:
    roast = normalize_reply(roast_reply)
    base = normalize_reply(base_reply)
    user = normalize_reply(user_message)
    if not roast or len(roast) > 2500:
        return False
    if roast in {"รับทราบครับ", "โอเคครับ", "รับทราบ", "โอเค"}:
        return False
    if not base or not user:
        return False

    # Keep the roast reasonably close to the factual answer.
    base_tokens = {x for x in re.findall(r"[\u0E00-\u0E7F]{3,}|[A-Za-z0-9]{3,}", base.lower())}
    roast_tokens = {x for x in re.findall(r"[\u0E00-\u0E7F]{3,}|[A-Za-z0-9]{3,}", roast.lower())}
    if base_tokens:
        overlap = len(base_tokens & roast_tokens) / max(1, len(base_tokens))
        if overlap < 0.18:
            return False

    return True
