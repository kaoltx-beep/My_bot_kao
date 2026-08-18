"""Telegram transport handlers for Jarvis."""

from __future__ import annotations

from typing import Any


def _result_text(result: Any) -> str:
    if result is None:
        return "รับทราบครับ"
    if isinstance(result, str):
        return result
    if hasattr(result, "success"):
        if getattr(result, "success", False):
            data = getattr(result, "data", None)
            return str(data) if data is not None else "ดำเนินการสำเร็จครับ"
        return f"ดำเนินการไม่สำเร็จ: {getattr(result, 'error', 'unknown error')}"
    return str(result)


def register_handlers(bot: Any, tool_system: Any = None) -> None:
    """Register Telegram message handlers."""

    @bot.message_handler(func=lambda message: bool(getattr(message, "text", None)))
    def handle_message(message: Any) -> None:
        text = message.text.strip()
        if not text:
            return

        try:
            if tool_system is not None:
                _call, result = tool_system.execute_text(text)
                reply = _result_text(result)
            else:
                reply = f"ได้รับข้อความแล้วครับ: {text}"
        except Exception as exc:
            reply = f"เกิดข้อผิดพลาดในการประมวลผลครับ: {exc}"

        bot.send_message(message.chat.id, reply)
