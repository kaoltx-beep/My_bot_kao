"""Telegram transport handler with owner-bound, one-use tool approvals."""

from __future__ import annotations

import threading
from typing import Any

def process_message(text: str) -> dict[str, Any]:
    """Load the FastAPI-backed chat pipeline only when a normal chat message arrives."""
    from .chat import process_message as _process_message
    return _process_message(text)


def _allowed_chat_id() -> int:
    try:
        import config
        return int(getattr(config, "TELEGRAM_CHAT_ID", 0) or 0)
    except (ImportError, TypeError, ValueError):
        return 0


def register_handlers(bot: Any, tool_system: Any = None) -> None:
    """Register Telegram messages and approval callbacks for one private chat."""

    @bot.callback_query_handler(func=lambda call: bool(
        getattr(call, "data", "") and call.data.startswith("jarvis_approval:")
    ))
    def handle_tool_approval(call: Any) -> None:
        from core import approval

        try:
            chat_id = int(call.message.chat.id)
            user_id = int(call.from_user.id)
            message_id = int(call.message.message_id)
        except (AttributeError, TypeError, ValueError):
            bot.answer_callback_query(call.id, "ข้อมูลผู้อนุมัติไม่ถูกต้อง")
            return

        allowed_chat_id = _allowed_chat_id()
        if allowed_chat_id <= 0 or chat_id != allowed_chat_id or user_id <= 0:
            bot.answer_callback_query(call.id, "ไม่ได้รับอนุญาต")
            return

        parts = call.data.split(":", 2)
        if len(parts) != 3 or parts[1] not in {"approve", "reject"}:
            bot.answer_callback_query(call.id, "คำสั่งอนุมัติไม่ถูกต้อง")
            return

        action, approval_id = parts[1], parts[2]
        status = "approved" if action == "approve" else "rejected"
        item = approval.consume(
            approval_id,
            status,
            chat_id=chat_id,
            user_id=user_id,
            message_id=message_id,
        )
        if item is None:
            bot.answer_callback_query(call.id, "คำขอหมดอายุ ถูกใช้แล้ว หรือไม่ใช่ของคุณ")
            return

        if status == "rejected":
            bot.answer_callback_query(call.id, "ยกเลิกคำขอแล้ว")
            bot.edit_message_text(
                f"❌ ยกเลิกคำขอ: {item['tool']}",
                chat_id,
                message_id,
            )
            return

        if tool_system is None:
            bot.answer_callback_query(call.id, "ระบบ Tool ยังไม่พร้อม")
            bot.edit_message_text("⚠️ ระบบ Tool ยังไม่พร้อม จึงไม่ได้เรียกใช้งาน", chat_id, message_id)
            return

        tool = tool_system.registry.get(item["tool"])
        if tool is None:
            bot.answer_callback_query(call.id, "ไม่พบ Tool ที่ขออนุมัติ")
            bot.edit_message_text("❌ ไม่พบ Tool ที่ขออนุมัติ จึงไม่ได้เรียกใช้งาน", chat_id, message_id)
            return

        result = tool_system.execute(
            item["tool"],
            item["params"],
            approved=True,
            approval_grant=item.get("approval_grant"),
        )
        bot.answer_callback_query(call.id, "อนุมัติแล้ว")
        if not getattr(result, "success", False):
            detail = getattr(result, "error", None) or "ไม่ทราบสาเหตุ"
            bot.edit_message_text(
                f"❌ Tool ทำงานไม่สำเร็จ\n{item['tool']}\n{detail}",
                chat_id,
                message_id,
            )
            return

        data = str(getattr(result, "data", None))
        if len(data) > 3000:
            data = data[:3000] + "\n… [ตัดข้อความ]"
        bot.edit_message_text(
            f"✅ อนุมัติและทำงานแล้ว\n{item['tool']}\n{data}",
            chat_id,
            message_id,
        )

    @bot.message_handler(func=lambda message: bool(getattr(message, "text", None)))
    def handle_message(message: Any) -> None:
        # Fail closed: an unset/invalid allow-list must never expose the bot.
        try:
            allowed_chat_id = _allowed_chat_id()
            incoming_chat_id = int(message.chat.id)
            user_id = int(message.from_user.id)
        except (AttributeError, TypeError, ValueError):
            return

        if allowed_chat_id <= 0 or incoming_chat_id != allowed_chat_id or user_id <= 0:
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

        # High/medium-risk tools must pause for a one-use approval before execution.
        if tool_system is not None:
            try:
                call = tool_system.parse(text)
                tool = tool_system.registry.get(call.tool_name) if call is not None else None
                if call is not None and tool is not None:
                    metadata = tool.metadata
                    risk = str(getattr(metadata, "risk_level", "unknown")).lower()
                    needs_approval = bool(getattr(metadata, "require_approval", False)) or risk != "low"
                    if needs_approval:
                        from core import approval
                        import telebot

                        approval_id = approval.create(
                            call.tool_name,
                            call.params,
                            incoming_chat_id,
                            user_id,
                        )
                        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
                        markup.add(
                            telebot.types.InlineKeyboardButton(
                                "✅ อนุมัติ", callback_data=f"jarvis_approval:approve:{approval_id}"
                            ),
                            telebot.types.InlineKeyboardButton(
                                "❌ ยกเลิก", callback_data=f"jarvis_approval:reject:{approval_id}"
                            ),
                        )
                        sent = bot.send_message(
                            incoming_chat_id,
                            f"🛡 ต้องอนุมัติก่อนดำเนินการ\nTool: {call.tool_name}\nพารามิเตอร์: {call.params}\nหมดอายุใน 5 นาที",
                            reply_markup=markup,
                        )
                        if not approval.bind_message(
                            approval_id,
                            chat_id=incoming_chat_id,
                            user_id=user_id,
                            message_id=int(sent.message_id),
                        ):
                            bot.edit_message_text(
                                "⚠️ ผูกคำขออนุมัติไม่สำเร็จ จึงยกเลิกคำขอ",
                                incoming_chat_id,
                                int(sent.message_id),
                            )
                        return
            except Exception:
                # Do not fall through to chat execution if approval routing failed.
                bot.send_message(incoming_chat_id, "ระบบอนุมัติไม่พร้อม จึงไม่ได้เรียก Tool")
                return

        try:
            result = process_message(text)
            reply = result.get("reply") or result.get("message") or "ดำเนินการสำเร็จ"
        except Exception:
            reply = "เกิดข้อผิดพลาดในการประมวลผล กรุณาลองใหม่"
        bot.send_message(incoming_chat_id, str(reply))
