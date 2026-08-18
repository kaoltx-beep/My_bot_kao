"""Telegram handler registration.

Kept intentionally small: run.py supplies the application callback and bot
instance so transport code does not own Jarvis business logic.
"""

from __future__ import annotations

from typing import Any, Callable


def register_handlers(bot: Any, callback: Callable[[str], str]) -> None:
    @bot.message_handler(func=lambda message: bool(getattr(message, "text", None)))
    def _handle(message: Any) -> None:
        reply = callback(message.text)
        bot.send_message(message.chat.id, reply)
