import json
import logging
import os
import subprocess
import sys
import threading
import traceback
from queue import Queue
from pathlib import Path

import telebot
from fastapi import FastAPI, Header, HTTPException
from groq import Groq
import uvicorn

import auto_work
import config
import developer_mode_router
import device_actions
import intent_router
import memory_manager_v2 as memory_manager
import personality
import plugin_loader
import plugin_router
import reminder_worker
import smart_router  # noqa: F401
import tts
import voice_stt
from core.approval import consume as consume_approval
from core.approval import create as create_approval
from core.tool_system import JarvisToolSystem
from expense_manager import monthly_summary
from job_database import list_jobs, pending_jobs, search_jobs

plugin_loader.load_plugins()

PLUGIN_MAP = {
    "check_battery": "battery",
    "open_youtube": "youtube",
    "news": "news",
    "add_expense": "expense",
    "monthly_expense": "expense",
    "list_expense": "expense",
    "task": "task",
    "reminder": "reminder",
    "work": "work",
}

_DASHBOARD_TOKEN = os.getenv("DASHBOARD_TOKEN", "")
app = FastAPI()


def _check_dashboard_auth(x_dashboard_token: str = Header(default=None)):
    if _DASHBOARD_TOKEN and x_dashboard_token != _DASHBOARD_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(config.TELEGRAM_TOKEN)
client = Groq(api_key=config.GROQ_API_KEY)
task_queue = Queue()
tool_system = JarvisToolSystem()
ROOT = Path(__file__).resolve().parent


def _try_tool_system(text, chat_id=None):
    """Parse and route explicit V1 tools. High-risk tools wait for Telegram approval."""
    try:
        call = tool_system.parse(text)
        if call is None:
            return None

        tool = tool_system.registry.get(call.tool_name)
        if tool is None:
            return None

        if tool.metadata.risk_level in {"high", "critical"}:
            if chat_id is None:
                return None
            approval_id = create_approval(call.tool_name, call.params, int(chat_id))
            markup = telebot.types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                telebot.types.InlineKeyboardButton(
                    "✅ อนุมัติ", callback_data=f"tool_approval:approve:{approval_id}"
                ),
                telebot.types.InlineKeyboardButton(
                    "❌ ยกเลิก", callback_data=f"tool_approval:reject:{approval_id}"
                ),
            )
            return {
                "handled": True,
                "reply": (
                    f"🛡 ต้องอนุมัติก่อน\n"
                    f"Tool: {call.tool_name}\n"
                    f"คำขอ: {call.params}\n"
                    f"รหัส: {approval_id}"
                ),
                "markup": markup,
            }

        if tool.metadata.risk_level not in {"low", "medium"}:
            return None

        result = tool_system.execute(call.tool_name, call.params)
        if not result.success:
            return {
                "handled": True,
                "reply": f"🛠 Tool {call.tool_name} ไม่สำเร็จ: {result.error}",
                "markup": None,
            }

        data = result.data
        if isinstance(data, list):
            data = "\n".join(
                " | ".join(map(str, row)) if isinstance(row, (list, tuple)) else str(row)
                for row in data
            )
        data = str(data)
        if len(data) > 3500:
            data = data[:3500] + "\n… [ตัดข้อความเพื่อป้องกัน Telegram message too long]"
        return {"handled": True, "reply": f"🧰 {call.tool_name}\n{data}", "markup": None}
    except Exception as exc:
        print("Tool System Error:", exc)
        return None


def _send_admin_alert(error_text: str):
    try:
        if config.TELEGRAM_CHAT_ID:
            short = str(error_text)[:500]
            bot.send_message(config.TELEGRAM_CHAT_ID, f"⚠️ Jarvis Error:\n{short}")
    except Exception:
        pass


def fallback_intent(text):
    text = text.lower()
    if "แบต" in text or "battery" in text:
        return "check_battery"
    if "youtube" in text or "ยูทูป" in text:
        return "open_youtube"
    if "ข่าว" in text or "news" in text:
        return "news"
    if "เดือนนี้" in text or "รายเดือน" in text:
        return "monthly_expense"
    if "ดูรายจ่าย" in text or "รายการรายจ่าย" in text:
        return "list_expense"
    if "ติดตั้ง" in text or "งานติดตั้ง" in text:
        return "work"
    if "ดูงานทั้งหมด" in text:
        return "list_jobs"
    if "งานที่" in text:
        return "search_jobs"
    if "บันทึกงาน" in text or "เพิ่มงาน" in text or "วันนี้มีงาน" in text:
        return "task"
    if "ตั้งเตือน" in text or "ดูรายการเตือน" in text or "ดูเตือน" in text:
        return "reminder"
    import re
    if re.search(r".+\s+\d+", text):
        return "add_expense"
    return None


def ask_jarvis(user_message, history_text=""):
    history_text = history_text[-3000:]
    system_instruction = """
คุณคือ Jarvis ผู้ช่วย AI ส่วนตัว
ตอบภาษาไทยเท่านั้น
พูดสุภาพ ลงท้ายครับ
ตอบสั้น กระชับ เข้าใจง่าย
ถ้าไม่แน่ใจ ให้บอกว่าไม่แน่ใจ
ห้ามสร้างตัวเลข ข้อมูลระบบ หรือผลการตรวจสอบที่ไม่มีจริง
ตอบเฉพาะ JSON
"""
    prompt = f"""Context:\n{history_text}\n\nUser:\n{user_message}\n\nตอบ JSON:\n{{\n  \"reply\":\"ข้อความตอบกลับ\",\n  \"action\":null\n}}"""
    try:
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
        )
        return json.loads(res.choices[0].message.content)
    except Exception as exc:
        print("AI Error:", exc)
        return {"reply": "ขออภัยครับ ระบบ AI ขัดข้องครับ", "action": None}


def _format_developer_result(result):
    files = result.get("files") or []
    if not files:
        return "🛠 Developer Mode\nไม่พบไฟล์ที่ตรงกับคำสั่งครับ"
    lines = ["🛠 Developer Mode", f"ตรวจพบ {len(files)} ไฟล์:"]
    for item in files[:20]:
        status = "✅" if item.get("status") == "ok" else "❌"
        path = item.get("file", "unknown")
        if item.get("status") == "ok":
            lines.append(f"{status} {path} ({item.get('lines', 0)} บรรทัด)")
        else:
            errors = "; ".join(item.get("errors", []))[:180]
            lines.append(f"{status} {path}: {errors}")
    return "\n".join(lines)


def worker():
    while True:
        task = task_queue.get()
        try:
            chat_id = task["chat_id"]
            text = task["text"]
            auto_saved = auto_work.save_auto_work(text)
            history = task["history"]
            history_text = "\n".join(f"User:{u}\nJarvis:{b}" for u, b in history)
            db_memory = memory_manager.get_memory(3)
            if db_memory:
                history_text += "\n\n[Previous Memory]\n" + "\n".join(
                    f"User:{u}\nJarvis:{b}" for u, b in db_memory
                )

            tool_system_reply = None
            tool_system_markup = None

            if "เปิดโหมดกวน" in text or "โหมดกวน" in text:
                personality.set_mode("ROAST")
                reply = "เปิดโหมดกวนแล้วครับ 😎"
            elif "กลับโหมดปกติ" in text or "โหมดปกติ" in text:
                personality.set_mode("NORMAL")
                reply = "กลับโหมดปกติแล้วครับ"
            else:
                tool_result = _try_tool_system(text, chat_id)
                if tool_result and tool_result.get("handled"):
                    tool_system_reply = tool_result["reply"]
                    tool_system_markup = tool_result.get("markup")
                    reply = tool_system_reply
                    auto_saved = "tool_system"
                    result = {"reply": tool_system_reply, "action": None}
                elif developer_mode_router.is_developer_command(text):
                    developer_result = developer_mode_router.execute_developer_command(text)
                    reply = _format_developer_result(developer_result)
                    result = {"reply": reply, "action": None}
                    auto_saved = "developer_mode"
                else:
                    result = ask_jarvis(text, history_text)

                action = intent_router.classify(text) or fallback_intent(text) or result.get("action")
                if isinstance(action, dict):
                    action = action.get("action") or action.get("intent") or action.get("name")
                elif isinstance(action, list):
                    action = action[0] if action else None
                if not isinstance(action, str):
                    action = None

                if auto_saved == "tool_system":
                    reply = tool_system_reply
                elif auto_saved == "developer_mode":
                    reply = result.get("reply") or reply
                elif auto_saved == "duplicate":
                    reply = "งานนี้ผมบันทึกไว้แล้วครับ"
                elif auto_saved is True:
                    reply = "บันทึกงานติดตั้งไฟเบอร์เสร็จแล้วครับ"
                else:
                    if action == "list_jobs":
                        reply = list_jobs()
                    elif action == "search_jobs":
                        reply = search_jobs(text.replace("งานที่", "").strip())
                    elif action == "pending_jobs":
                        reply = pending_jobs()
                    else:
                        reply = result.get("reply") or "รับทราบครับ"
                    plugin_name = None if auto_saved else PLUGIN_MAP.get(action)
                    if plugin_name:
                        plugin = plugin_loader.get_plugin(plugin_name)
                        if plugin:
                            reply = plugin.execute(text)
                    reply = reply.replace("ค่ะ", "ครับ").replace("คะ", "ครับ")

            print("DEBUG CHAT:", chat_id)
            print("DEBUG REPLY:", reply)
            if chat_id:
                if auto_saved == "tool_system" and tool_system_markup is not None:
                    bot.send_message(chat_id, reply, reply_markup=tool_system_markup)
                else:
                    bot.send_message(chat_id, reply, reply_markup=get_main_keyboard())
            try:
                tts.speak(reply)
            except Exception as exc:
                print("TTS Error:", exc)
            memory_manager.save_memory(text, reply)
        except Exception:
            traceback.print_exc()
            _send_admin_alert(traceback.format_exc())
        finally:
            task_queue.task_done()


def get_main_keyboard():
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(
        telebot.types.KeyboardButton("🤖 Jarvis Menu"),
        telebot.types.KeyboardButton("📋 งานล่าสุด"),
        telebot.types.KeyboardButton("💰 รายจ่าย"),
        telebot.types.KeyboardButton("➕ เพิ่มงาน"),
        telebot.types.KeyboardButton("💵 เพิ่มค่าใช้จ่าย"),
        telebot.types.KeyboardButton("🧠 ความจำ"),
        telebot.types.KeyboardButton("📊 รายงาน"),
        telebot.types.KeyboardButton("🔋 สถานะเครื่อง"),
        telebot.types.KeyboardButton("⏹ หยุดพูด"),
        telebot.types.KeyboardButton("❓ ช่วยเหลือ"),
    )
    return keyboard


@bot.callback_query_handler(func=lambda call: call.data.startswith("tool_approval:"))
def handle_tool_approval(call):
    if config.TELEGRAM_CHAT_ID and call.message and call.message.chat.id != config.TELEGRAM_CHAT_ID:
        bot.answer_callback_query(call.id, "ไม่ได้รับอนุญาต")
        return

    parts = call.data.split(":", 2)
    if len(parts) != 3:
        bot.answer_callback_query(call.id, "ข้อมูลอนุมัติไม่ถูกต้อง")
        return

    action, approval_id = parts[1], parts[2]
    status = "approved" if action == "approve" else "rejected" if action == "reject" else None
    if status is None:
        bot.answer_callback_query(call.id, "คำสั่งไม่ถูกต้อง")
        return

    item = consume_approval(approval_id, status)
    if item is None:
        bot.answer_callback_query(call.id, "คำขอนี้ถูกใช้ไปแล้วหรือหมดอายุ")
        return

    if status == "rejected":
        bot.answer_callback_query(call.id, "ยกเลิกแล้ว")
        bot.edit_message_text(
            "❌ ยกเลิก Tool: " + item["tool"],
            call.message.chat.id,
            call.message.message_id,
        )
        return

    result = tool_system.execute(item["tool"], item["params"], approved=True)
    bot.answer_callback_query(call.id, "อนุมัติแล้ว")
    if not result.success:
        bot.edit_message_text(
            f"❌ Tool ทำงานไม่สำเร็จ\n🧰 {item['tool']}\n{result.error}",
            call.message.chat.id,
            call.message.message_id,
        )
        return

    if item["tool"] == "file_write" and isinstance(result.data, dict):
        target = result.data.get("path", "")
        backup = result.data.get("backup_path")
        if str(target).endswith(".py") and backup:
            target_path = ROOT / target
            check = subprocess.run(
                [sys.executable, "-m", "py_compile", str(target_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if check.returncode != 0:
                try:
                    from tools.file_tool import restore_backup
                    restore_backup(backup, target)
                    bot.edit_message_text(
                        "⚠️ เขียนไฟล์แล้ว syntax ไม่ผ่าน จึง rollback อัตโนมัติ\n"
                        f"🧰 {item['tool']}\n{check.stderr[-1200:]}",
                        call.message.chat.id,
                        call.message.message_id,
                    )
                except Exception as rollback_error:
                    bot.edit_message_text(
                        f"❌ Syntax ไม่ผ่าน และ rollback ไม่สำเร็จ\n{rollback_error}",
                        call.message.chat.id,
                        call.message.message_id,
                    )
                return

    data = str(result.data)
    if len(data) > 3500:
        data = data[:3500] + "\n… [ตัดข้อความ]"
    bot.edit_message_text(
        f"✅ อนุมัติและทำงานแล้ว\n🧰 {item['tool']}\n{data}",
        call.message.chat.id,
        call.message.message_id,
    )


@bot.message_handler(commands=["start"])
def handle_start(message):
    if config.TELEGRAM_CHAT_ID and message.chat.id != config.TELEGRAM_CHAT_ID:
        return
    bot.send_message(
        message.chat.id,
        "สวัสดีครับ! ผมคือ Jarvis ผู้ช่วย AI ของคุณ\n\nเลือกเมนูด้านล่างครับ",
        reply_markup=get_main_keyboard(),
    )


@bot.message_handler(func=lambda message: True)
def handle(message):
    if config.TELEGRAM_CHAT_ID and message.chat.id != config.TELEGRAM_CHAT_ID:
        return
    if not message.text:
        return

    text = message.text.strip()[:2000]
    if not text:
        return

    if text == "⏹ หยุดพูด":
        stopped = tts.stop()
        bot.send_message(
            message.chat.id,
            "⏹ หยุดพูดแล้วครับ" if stopped else "⏹ ตอนนี้ไม่มีเสียงที่กำลังพูดครับ",
            reply_markup=get_main_keyboard(),
        )
        return

    if text == "🤖 Jarvis Menu":
        tts.stop()
        bot.send_message(
            message.chat.id,
            "🤖 Jarvis Menu\nเลือกคำสั่งจากปุ่มด้านล่างครับ",
            reply_markup=get_main_keyboard(),
        )
        return

    if text == "❓ ช่วยเหลือ":
        tts.stop()
        bot.send_message(
            message.chat.id,
            "❓ ช่วยเหลือ\nพิมพ์คำสั่งตามปกติได้เลยครับ หรือใช้ปุ่มเมนูด้านล่าง",
            reply_markup=get_main_keyboard(),
        )
        return

    task_queue.put(
        {
            "chat_id": message.chat.id,
            "text": text,
            "history": memory_manager.get_memory(5),
        }
    )


def voice_worker():
    print("🎤 Voice Mode Started")
    while True:
        try:
            text = voice_stt.listen_and_transcribe()
            if text:
                bot.send_message(config.TELEGRAM_CHAT_ID, f"🎤 {text}")
                task_queue.put(
                    {
                        "chat_id": config.TELEGRAM_CHAT_ID,
                        "text": text,
                        "history": memory_manager.get_memory(5),
                    }
                )
        except Exception as exc:
            print("Voice Error:", exc)


def telegram_polling():
    print("📡 Telegram polling started")
    bot.infinity_polling(
        timeout=20,
        long_polling_timeout=20,
        allowed_updates=["message", "callback_query"],
    )


if __name__ == "__main__":
    print("Jarvis started")
    threading.Thread(target=worker, daemon=True).start()
    threading.Thread(target=telegram_polling, daemon=True).start()
    if os.getenv("VOICE_MODE_ENABLED", "0") == "1":
        threading.Thread(target=voice_worker, daemon=True).start()
    threading.Thread(target=reminder_worker.run, daemon=True).start()
    uvicorn.run("run:app", host="127.0.0.1", port=8000, reload=False)
