"""Telegram transport handler using the shared Jarvis chat pipeline."""

from __future__ import annotations

import threading
from typing import Any

from .chat import process_message


def register_handlers(bot: Any, tool_system: Any = None) -> None:
    """Register Telegram messages against the same pipeline as /chat."""

    @bot.message_handler(func=lambda message: bool(getattr(message, "text", None)))
    def handle_message(message: Any) -> None:
        text = message.text.strip()
        if not text:
            return

        # Explicit device TTS commands. These must be handled here so they
        # do not get swallowed by the normal AI chat pipeline.
        if text == "/stop":
            try:
                from tts import stop
                stopped = stop()
                bot.send_message(
                    message.chat.id,
                    "หยุดเสียงแล้ว" if stopped else "ตอนนี้ไม่มีเสียงที่กำลังพูดอยู่",
                )
            except Exception as exc:
                bot.send_message(message.chat.id, f"หยุดเสียงไม่สำเร็จ: {exc}")
            return

        if text.startswith("/speak"):
            speech = text[len("/speak") :].strip()
            if not speech:
                bot.send_message(message.chat.id, "ใช้แบบนี้: /speak สวัสดีครับ นี่คือ Jarvis")
                return

            try:
                from tts import speak

                # Speak asynchronously so Telegram polling remains responsive.
                threading.Thread(target=speak, args=(speech,), daemon=True).start()
                bot.send_message(message.chat.id, "🔊 กำลังพูด: " + speech)
            except Exception as exc:
                bot.send_message(message.chat.id, f"TTS Error: {exc}")
            return

        try:
            result = process_message(text)
            reply = result.get("reply") or result.get("message") or "ดำเนินการสำเร็จ"
        except Exception as exc:
            reply = f"เกิดข้อผิดพลาดในการประมวลผล: {exc}"

        bot.send_message(message.chat.id, str(reply))
