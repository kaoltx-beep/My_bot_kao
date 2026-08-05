"""Telegram handlers for Jarvis.

This module exposes register_handlers(bot, tool_system=None) which registers
message and callback handlers on the provided TeleBot instance. It must not
create a TeleBot itself to avoid duplicate polling or circular imports.
"""
from __future__ import annotations

import threading
import time
from queue import Queue
from typing import Optional

import plugin_loader
import plugin_router

# Optional components imported lazily

def _safe_import(name: str):
    try:
        module = __import__(name)
    except Exception:
        module = None
    return module


def register_handlers(bot, tool_system=None):
    """Register handlers on the provided telebot.TeleBot instance.

    The function starts a worker thread which processes incoming messages
    placed on an internal queue by the message handler.
    """
    # Ensure plugins are loaded
    try:
        plugin_loader.load_plugins()
    except Exception as exc:
        print("Warning: plugin_loader.load_plugins failed:", exc)

    memory_store = _safe_import("memory_store")
    developer_mode_router = _safe_import("developer_mode_router")
    tts = _safe_import("tts")

    task_queue: Queue = Queue()

    def worker():
        print("Worker thread started")
        while True:
            task = task_queue.get()
            try:
                chat_id = task.get("chat_id")
                text = task.get("text") or ""

                # Developer Mode takes precedence
                if developer_mode_router and developer_mode_router.is_developer_command(text):
                    try:
                        result = developer_mode_router.execute_developer_command(text)
                        # result is a dict with files or error
                        files = result.get("files") or []
                        if files:
                            reply = "\n\n".join(f.get("file", "") for f in files)
                        else:
                            reply = result.get("error") or str(result)
                    except Exception as exc:
                        reply = f"Developer Mode error: {exc}"
                else:
                    # Friendly greetings and support phrases
                    normalized = text.strip().lower()
                    if any(greeting in normalized for greeting in ["สวัสดี", "หวัดดี", "hello", "hi", "hey", "สบายดี", "ดีไหม"]):
                       reply = "สวัสดีครับ! มีอะไรให้ Jarvis ช่วยได้บ้างครับ?"
                    elif any(menu_word in normalized for menu_word in ["เมนู", "menu", "jarvis menu", "ช่วยอะไร", "คำสั่ง", "ทำอะไรได้"]):
                       plugin_info = plugin_loader.get_plugin_info()
                       if plugin_info:
                          plugin_list = [f"{name}: {meta.get('description', '')}" for name, meta in plugin_info.items()]
                          reply = "Jarvis สามารถช่วยได้ดังนี้:\n" + "\n".join(plugin_list)
                       else:
                          reply = "Jarvis มีคำสั่งพื้นฐาน เช่น สวัสดี, ดูข่าว, เช็คแบตเตอรี่, บันทึกค่าใช้จ่าย, ตั้งเตือน"
                    else:
                       # Plugin routing
                       plugin_name = plugin_router.find_plugin(text)
                       reply = None
                       if plugin_name:
                           plugin = plugin_loader.get_plugin(plugin_name)
                           if plugin:
                               try:
                                   reply = plugin.execute(text)
                               except Exception as exc:
                                   reply = f"Plugin {plugin_name} error: {exc}"

                    if not reply:
                        # Basic fallback
                        reply = "รับทราบครับ"  # simple default reply

                # Send reply
                if chat_id:
                    try:
                        bot.send_message(chat_id, reply)
                    except Exception as exc:
                        print("Failed to send message:", exc)

                # Try speaking (non-blocking)
                if tts:
                    try:
                        t = threading.Thread(target=lambda: tts.speak(reply), daemon=True)
                        t.start()
                    except Exception:
                        pass

                # Save memory if memory_store provides a save API
                try:
                    if memory_store and hasattr(memory_store, "add_memory"):
                        # Simple heuristic: if plugin 'memory' handled it, skip
                        if not (plugin_name == "memory"):
                            # store user message and reply as memory candidate
                            try:
                                memory_store.add_memory("conversation", f"User: {text} → Jarvis: {reply}")
                            except Exception:
                                pass
                except Exception:
                    pass

            except Exception as exc:
                print("Worker error:", exc)
            finally:
                task_queue.task_done()

    threading.Thread(target=worker, daemon=True).start()

    # Message handler: enqueue incoming text messages
    def _on_message(message):
        chat_id = getattr(message.chat, "id", None)
        text = getattr(message, "text", "")
        task_queue.put({"chat_id": chat_id, "text": text})

    bot.message_handler(func=lambda m: True)(_on_message)

    # Callback query handler: delegate to approval flow if available
    def _on_callback(call):
        data = getattr(call, "data", "") or ""
        try:
            # If this is a tool approval callback and core.approval exists, handle it
            if data.startswith("tool_approval:"):
                core_approval = _safe_import("core.approval")
                tool_system_local = tool_system
                if core_approval is None or tool_system_local is None:
                    # not integrated — acknowledge only
                    try:
                        bot.answer_callback_query(call.id, "Feature not available")
                    except Exception:
                        pass
                    return

                # parts: tool_approval:approve:<id>
                parts = data.split(":", 2)
                if len(parts) != 3:
                    bot.answer_callback_query(call.id, "ข้อมูลอนุมัติไม่ถูกต้อง")
                    return
                action, approval_id = parts[1], parts[2]
                status = "approved" if action == "approve" else "rejected" if action == "reject" else None
                if status is None:
                    bot.answer_callback_query(call.id, "คำสั่งไม่ถูกต้อง")
                    return

                item = core_approval.consume(approval_id, status)
                if item is None:
                    bot.answer_callback_query(call.id, "คำขอนี้ถูกใช้ไปแล้วหรือหมดอายุ")
                    return

                if status == "rejected":
                    bot.answer_callback_query(call.id, "ยกเลิกแล้ว")
                    try:
                        bot.edit_message_text("❌ ยกเลิก Tool: " + item["tool"], call.message.chat.id, call.message.message_id)
                    except Exception:
                        pass
                    return

                result = tool_system_local.execute(item["tool"], item.get("params"), approved=True)
                bot.answer_callback_query(call.id, "อนุมัติแล้ว")

                if not getattr(result, "success", True):
                    try:
                        bot.edit_message_text(f"❌ Tool ทำงานไม่สำเร็จ\\n🧰 {item['tool']}\\n{getattr(result, 'error', str(result))}", call.message.chat.id, call.message.message_id)
                    except Exception:
                        pass
                    return

                data_text = str(getattr(result, "data", result))
                if len(data_text) > 3500:
                    data_text = data_text[:3500] + "\n… [ตัดข้อความ]"
                try:
                    bot.edit_message_text(f"✅ อนุมัติและทำงานแล้ว\\n🧰 {item['tool']}\\n{data_text}", call.message.chat.id, call.message.message_id)
                except Exception:
                    pass
                return

            # Generic acknowledgement for other callbacks
            bot.answer_callback_query(call.id, "ได้รับการคลิกแล้ว")
        except Exception as exc:
            print("Callback handler error:", exc)

    bot.callback_query_handler(func=lambda call: True)(_on_callback)

    print("Handlers registered")
    return True
