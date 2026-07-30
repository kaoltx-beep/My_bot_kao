from __future__ import annotations


def reply(text: str) -> str | None:
    """Deterministic replies for common short phrases in ROAST mode."""
    t = (text or "").strip().lower()
    if not t:
        return None

    if t in {"วันนี้เป็นไง", "วันนี้เป็นไงบ้าง", "วันนี้เป็นอย่างไร", "วันนี้เป็นไงบ้าง"}:
        return "วันนี้ก็โอเคครับ แต่ถ้ามึงถามเพราะนั่งเหงาอยู่ ก็พูดมาตรงๆ ไอ้บ้า"

    if t in {"หรอ", "เหรอ", "จริงดิ", "จริงเหรอ"}:
        return "เออสิครับ มึงจะให้กูเสกข่าวดราม่าจากอากาศอีกหรือไง"

    if t in {"มึงพูดอะไร", "พูดอะไร", "คืออะไรวะ", "คืออะไร"}:
        return "กูกำลังตอบมึงอยู่ครับ แค่เมื่อกี้ไอ้โมเดลมันพูดเละเอง คราวนี้เอาแบบภาษาคนแล้ว"

    if t in {"สวัสดี", "หวัดดี", "hello", "hi"}:
        return "หวัดดีครับ ไอ้ตัวป่วน วันนี้จะให้กูช่วยอะไรอีก"

    return None
