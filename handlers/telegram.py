"""Telegram transport handler using the shared Jarvis chat pipeline."""

from __future__ import annotations

from typing import Any

from .chat import process_message


def register_handlers(bot: Any, tool_system: Any = None) -> None:
    """Register Telegram messages against the same pipeline as /chat."""

    @bot.message_handler(func=lambda message: bool(getattr(message, "text", None)))
    def handle_message(message: Any) -> None:
        text = message.text.strip()
        if not text:
            return

        try:
            result = process_message(text)
            reply = result.get("reply") or result.get("message") or "ดำเนินการสำเร็จ"
        except Exception as exc:
            reply = f"เกิดข้อผิดพลาดในการประมวลผล: {exc}"

        bot.send_message(message.chat.id, str(reply))
