"""Telegram transport handler using the shared Jarvis chat pipeline."""

from __future__ import annotations

import threading
from typing import Any

from .chat import process_message


def register_handlers(bot: Any, tool_system: Any = None) -> None:
    """Register Telegram messages; accept only the configured private chat."""

    @bot.message_handler(func=lambda message: bool(getattr(message, "text", None)))
    def handle_message(message: Any) -> None:
        # Fail closed: an unset/invalid allow-list must never expose the bot.
        try:
            import config
            allowed_chat_id = int(getattr(config, "TELEGRAM_CHAT_ID", 0) or 0)
            incoming_chat_id = int(message.chat.id)
        except (ImportError, AttributeError, TypeError, ValueError):
            return

        if allowed_chat_id <= 0 or incoming_chat_id != allowed_chat_id:
            return

        text = message.text.strip()
        if not text:
            return

        if text == "/stop":
            try:
                from tts import stop
                stopped = stop()
                bot.send_message(
                    message.chat.id,
                    "หยุดเสียงแล้ว" if stopped else "ตอนนี้ไม่มีเสียงที่กำลังพูดอยู่",
                )
            except Exception:
                bot.send_message(message.chat.id, "หยุดเสียงไม่สำเร็จ")
            return

        if text.startswith("/speak"):
            speech = text[len("/speak") :].strip()
            if not speech:
                bot.send_message(message.chat.id, "ใช้แบบนี้: /speak สวัสดีครับ นี่คือ Jarvis")
                return

            try:
                from tts import speak
                threading.Thread(target=speak, args=(speech,), daemon=True).start()
                bot.send_message(message.chat.id, "🔊 กำลังพูด: " + speech)
            except Exception:
                bot.send_message(message.chat.id, "เริ่มระบบเสียงไม่สำเร็จ")
            return

        try:
            result = process_message(text)
            reply = result.get("reply") or result.get("message") or "ดำเนินการสำเร็จ"
        except Exception:
            reply = "เกิดข้อผิดพลาดในการประมวลผล กรุณาลองใหม่"
        bot.send_message(message.chat.id, str(reply))
