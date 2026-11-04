"""Telegram transport handler using the shared Jarvis chat pipeline."""

from __future__ import annotations

import threading
from typing import Any

from .chat import process_message
import developer_mode
from developer_mode_router import execute_developer_command, is_developer_command


def register_handlers(bot: Any, tool_system: Any = None) -> None:
    """Register Telegram messages; accept only the configured private chat."""

    @bot.message_handler(func=lambda message: bool(getattr(message, "text", None)))
    def handle_message(message: Any) -> None:
        text = (getattr(message, "text", "") or "").strip()
        if text == "/myid":
            if getattr(message.chat, "type", "") != "private":
                bot.send_message(message.chat.id, "เพื่อความเป็นส่วนตัว ให้ส่ง /myid ในแชทส่วนตัวกับบอท")
                return
            actor_id = getattr(getattr(message, "from_user", None), "id", None)
            bot.send_message(message.chat.id, f"Telegram User ID: {actor_id}" if actor_id is not None else "อ่าน Telegram User ID ไม่ได้")
            return

        # Fail closed: an unset/invalid allow-list must never expose the bot.
        try:
            import config
            allowed_chat_id = int(getattr(config, "TELEGRAM_CHAT_ID", 0) or 0)
            incoming_chat_id = int(message.chat.id)
        except (ImportError, AttributeError, TypeError, ValueError):
            return

        if allowed_chat_id <= 0 or incoming_chat_id != allowed_chat_id:
            return

        if not text:
            return

        if is_developer_command(text):
            actor_id = getattr(getattr(message, "from_user", None), "id", None)
            if not developer_mode.is_authorized_admin(actor_id):
                bot.send_message(message.chat.id, "⛔ ไม่มีสิทธิ์ใช้งาน Developer Mode")
                return
            try:
                result = execute_developer_command(text, actor_id=actor_id)
                files = result.get("files") or []
                reply = "\n".join(str(item.get("file") or item.get("errors") or "") for item in files).strip()
                bot.send_message(message.chat.id, reply or "Developer Mode ทำงานแล้ว แต่ไม่มีข้อความตอบกลับ")
            except Exception:
                bot.send_message(message.chat.id, "Developer Mode เกิดข้อผิดพลาด")
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
