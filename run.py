import os
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
from core.response_style import ROAST_STYLE_PROMPT, valid_base_reply, valid_roast_reply
from core.tool_system import JarvisToolSystem
from expense_manager import monthly_summary
from job_database import list_jobs, pending_jobs, search_jobs, tomorrow_jobs

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
            bot.send_message(config.TELEGRAM_CHAT_ID, f"⚠️ Jarvis Error:\n{str(error_text)[:500]}")
    except Exception:
        pass


def fallback_intent(text):
    text = text.lower().strip()
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
    if "พรุ่งนี้มีงาน" in text or "วันพรุ่งนี้มีงาน" in text:
        return "tomorrow_jobs"
    if "งานค้าง" in text or "งานที่ยังไม่เสร็จ" in text:
        return "pending_jobs"
    if "ติดตั้ง" in text or "งานติดตั้ง" in text:
        return "work"
    if "ดูงานทั้งหมด" in text or "งานล่าสุด" in text:
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


def _normalize_action(action):
    if isinstance(action, dict):
        action = action.get("action") or action.get("intent") or action.get("name")
    elif isinstance(action, list):
        action = action[0] if action else None
    return action if isinstance(action, str) else None


def _deterministic_action(action, text):
    if action == "list_jobs":
        return list_jobs()
    if action == "pending_jobs":
        return pending_jobs()
    if action == "tomorrow_jobs":
        return tomorrow_jobs()
    if action == "search_jobs":
        return search_jobs(text.replace("งานที่", "").strip())
    if action == "monthly_expense":
        return monthly_summary()

    plugin_name = PLUGIN_MAP.get(action)
    if plugin_name:
        plugin = plugin_loader.get_plugin(plugin_name)
        if plugin:
            return plugin.execute(text)
    return None


def _groq_json(system_prompt, user_prompt):
    try:
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        payload = json.loads(res.choices[0].message.content)
        return payload if isinstance(payload, dict) else None
    except Exception as exc:
        print("AI Error:", exc)
        return None


def ask_jarvis(user_message, history_text=""):
    mode = personality.get_mode()
    safe_history = history_text[-2500:] if mode != "ROAST" else ""
    base_system = personality.get_base_prompt() + "\nตอบเฉพาะ JSON: {\"reply\":\"...\",\"action\":null}\n"
    base_prompt = f"""Context จากการสนทนาก่อนหน้า (อาจผิดและห้ามถือเป็นข้อเท็จจริง):\n{safe_history}\n\nUser ล่าสุด:\n{user_message}\n\nตอบคำถามล่าสุดให้ตรงที่สุด"""

    base_result = _groq_json(base_system, base_prompt)
    base_reply = str((base_result or {}).get("reply") or "").strip()
    if not valid_base_reply(base_reply):
        base_reply = "ขออภัยครับ ตอนนี้ผมยังตอบคำถามนี้อย่างมั่นใจไม่ได้ครับ"
        base_result = {"reply": base_reply, "action": None}

    if mode != "ROAST":
        return base_result

    roast_prompt = (
        f"USER MESSAGE:\n{user_message}\n\n"
        f"BASE ANSWER:\n{base_reply}\n\n"
        "เปลี่ยนเฉพาะน้ำเสียงตามกฎ Roast โดยรักษาความหมายเดิมทั้งหมด"
    )
    roast_result = _groq_json(ROAST_STYLE_PROMPT, roast_prompt)
    roast_reply = str((roast_result or {}).get("reply") or "").strip()
    if valid_roast_reply(user_message, base_reply, roast_reply):
        return {"reply": roast_reply, "action": None}

    return base_result


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

            if "เปิดโหมดกวน" in text or "โหมดกวน" in text or "โหมดกวนตีน" in text:
                personality.set_mode("ROAST")
                reply = "เปิดโหมดกวนตีนแล้วครับ 😈 แต่ยังตอบเรื่องจริงให้ตรงคำถามนะ"
                auto_saved = "personality"
            elif "กลับโหมดปกติ" in text or "โหมดปกติ" in text:
                personality.set_mode("NORMAL")
                reply = "กลับโหมดปกติแล้วครับ"
                auto_saved = "personality"
            else:
                tool_result = _try_tool_system(text, chat_id)
                if tool_result and tool_result.get("handled"):
                    reply = tool_result["reply"]
                    markup = tool_result.get("markup")
                    if chat_id:
                        bot.send_message(chat_id, reply, reply_markup=markup)
                    try:
                        tts.speak(reply)
                    except Exception as exc:
                        print("TTS Error:", exc)
                    memory_manager.save_memory(text, reply)
                    continue

                if developer_mode_router.is_developer_command(text):
                    developer_result = developer_mode_router.execute_developer_command(text)
                    reply = _format_developer_result(developer_result)
                else:
                    action = _normalize_action(intent_router.classify(text) or fallback_intent(text))
                    deterministic_reply = _deterministic_action(action, text) if action else None
                    if deterministic_reply is not None:
                        reply = deterministic_reply
                    else:
                        result = ask_jarvis(text, history_text)
                        reply = str(result.get("reply") or "ขออภัยครับ ยังตอบคำถามนี้ไม่ได้ครับ")
                        ai_action = _normalize_action(result.get("action"))
                        if ai_action and ai_action != action:
                            routed = _deterministic_action(ai_action, text)
                            if routed is not None:
                                reply = routed

                    if auto_saved == "duplicate":
                        reply = "งานนี้ผมบันทึกไว้แล้วครับ"
                    elif auto_saved is True:
                        reply = "บันทึกงานติดตั้งไฟเบอร์เสร็จแล้วครับ"

            reply = reply.replace("ค่ะ", "ครับ").replace("คะ", "ครับ")
            print("DEBUG CHAT:", chat_id)
            print("DEBUG REPLY:", reply)
            if chat_id:
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
        bot.edit_message_text("❌ ยกเลิก Tool: " + item["tool"], call.message.chat.id, call.message.message_id)
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
            check = subprocess.run(
                [sys.executable, "-m", "py_compile", str(ROOT / target)],
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
    bot.send_message(message.chat.id, "สวัสดีครับ! ผมคือ Jarvis ผู้ช่วย AI ของคุณ\n\nเลือกเมนูด้านล่างครับ", reply_markup=get_main_keyboard())


@bot.message_handler(commands=["roast"])
def handle_roast(message):
    if config.TELEGRAM_CHAT_ID and message.chat.id != config.TELEGRAM_CHAT_ID:
        return
    personality.set_mode("ROAST")
    bot.send_message(message.chat.id, "😈 เปิดโหมดกวนตีนแล้วครับ แต่จะตอบเรื่องจริงก่อนค่อยกวน", reply_markup=get_main_keyboard())


@bot.message_handler(commands=["normal"])
def handle_normal(message):
    if config.TELEGRAM_CHAT_ID and message.chat.id != config.TELEGRAM_CHAT_ID:
        return
    personality.set_mode("NORMAL")
    bot.send_message(message.chat.id, "กลับโหมดปกติแล้วครับ", reply_markup=get_main_keyboard())


@bot.message_handler(commands=["help"])
def handle_help(message):
    if config.TELEGRAM_CHAT_ID and message.chat.id != config.TELEGRAM_CHAT_ID:
        return
    tts.stop()
    bot.send_message(
        message.chat.id,
        "🤖 คำสั่งหลัก\n/roast = เปิดโหมดกวนตีน\n/normal = กลับโหมดปกติ\n/start = เปิดเมนู\n/help = ช่วยเหลือ\n\nหรือใช้ปุ่มด้านล่างครับ",
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
        bot.send_message(message.chat.id, "⏹ หยุดพูดแล้วครับ" if stopped else "⏹ ตอนนี้ไม่มีเสียงที่กำลังพูดครับ", reply_markup=get_main_keyboard())
        return

    if text == "🤖 Jarvis Menu":
        tts.stop()
        bot.send_message(message.chat.id, "🤖 Jarvis Menu\nเลือกคำสั่งจากปุ่มด้านล่างครับ", reply_markup=get_main_keyboard())
        return

    if text == "❓ ช่วยเหลือ":
        tts.stop()
        bot.send_message(message.chat.id, "❓ ช่วยเหลือ\nพิมพ์คำสั่งตามปกติได้เลยครับ หรือใช้ปุ่มเมนูด้านล่าง", reply_markup=get_main_keyboard())
        return

    if text in {"🔥 โหมดกวนตีน", "😈 โหมดกวน"}:
        personality.set_mode("ROAST")
        bot.send_message(message.chat.id, "😈 เปิดโหมดกวนตีนแล้วครับ แต่จะตอบเรื่องจริงก่อนค่อยกวน", reply_markup=get_main_keyboard())
        return

    if text == "🙂 โหมดปกติ":
        personality.set_mode("NORMAL")
        bot.send_message(message.chat.id, "กลับโหมดปกติแล้วครับ", reply_markup=get_main_keyboard())
        return

    task_queue.put({"chat_id": message.chat.id, "text": text, "history": memory_manager.get_memory(5)})


def voice_worker():
    print("🎤 Voice Mode Started")
    while True:
        try:
            text = voice_stt.listen_and_transcribe()
            if text:
                bot.send_message(config.TELEGRAM_CHAT_ID, f"🎤 {text}")
                task_queue.put({"chat_id": config.TELEGRAM_CHAT_ID, "text": text, "history": memory_manager.get_memory(5)})
        except Exception as exc:
            print("Voice Error:", exc)


def telegram_polling():
    print("📡 Telegram polling started")
    bot.infinity_polling(timeout=20, long_polling_timeout=20, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    print("Jarvis started")
    threading.Thread(target=worker, daemon=True).start()
    threading.Thread(target=telegram_polling, daemon=True).start()
    if os.getenv("VOICE_MODE_ENABLED", "0") == "1":
        threading.Thread(target=voice_worker, daemon=True).start()
    threading.Thread(target=reminder_worker.run, daemon=True).start()
    uvicorn.run("run:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=False)
