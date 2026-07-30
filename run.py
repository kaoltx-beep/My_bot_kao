import threading
import time
import logging
import json
import traceback
from queue import Queue
import telebot
from groq import Groq

import config
import device_actions
import plugin_loader
from job_database import list_jobs, search_jobs, pending_jobs
from expense_manager import monthly_summary
import plugin_router
import intent_router
import developer_mode_router
plugin_loader.load_plugins()
import personality
import smart_router  # noqa: F401 – stub kept for compat
import auto_work
from core.tool_system import JarvisToolSystem
from core.approval import create as create_approval, consume as consume_approval

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

import memory_manager_v2 as memory_manager
import tts
import voice_stt
import reminder_worker

import os
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
import uvicorn

_DASHBOARD_TOKEN = os.getenv("DASHBOARD_TOKEN", "")


def _check_dashboard_auth(x_dashboard_token: str = Header(default=None)):
    """Require X-Dashboard-Token header when DASHBOARD_TOKEN env var is set."""
    if _DASHBOARD_TOKEN and x_dashboard_token != _DASHBOARD_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(config.TELEGRAM_TOKEN)
client = Groq(api_key=config.GROQ_API_KEY)

task_queue = Queue()
tool_system = JarvisToolSystem()


def _try_tool_system(text, chat_id=None):
    """V1 approval-aware bridge. Low-risk tools execute; high-risk tools pause for approval."""
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
                telebot.types.InlineKeyboardButton("✅ อนุมัติ", callback_data=f"tool_approval:approve:{approval_id}"),
                telebot.types.InlineKeyboardButton("❌ ยกเลิก", callback_data=f"tool_approval:reject:{approval_id}"),
            )
            return {
                "handled": True,
                "reply": f"🛡 ต้องอนุมัติก่อน\nTool: {call.tool_name}\nคำขอ: {call.params}\nรหัส: {approval_id}",
                "markup": markup,
            }

        if tool.metadata.risk_level not in {"low", "medium"}:
            return None

        result = tool_system.execute(call.tool_name, call.params)
        if not result.success:
            return {"handled": True, "reply": f"🛠 Tool {call.tool_name} ไม่สำเร็จ: {result.error}", "markup": None}

        data = result.data
        if isinstance(data, list):
            data = "\n".join(" | ".join(map(str, row)) if isinstance(row, (list, tuple)) else str(row) for row in data)
        data = str(data)
        max_chars = 3500
        if len(data) > max_chars:
            data = data[:max_chars] + "\n… [ตัดข้อความเพื่อป้องกัน Telegram message too long]"
        return {"handled": True, "reply": f"🧰 {call.tool_name}\n{data}", "markup": None}
    except Exception as exc:
        print("Tool System Error:", exc)
        return None


def _send_admin_alert(error_text: str):
    """Send a crash/error notification to the admin chat."""
    try:
        if config.TELEGRAM_CHAT_ID:
            short = str(error_text)[:500]
            bot.send_message(config.TELEGRAM_CHAT_ID, f"⚠️ Jarvis Error:\n{short}")
    except Exception:
        pass  # Never let error reporting itself crash the bot


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
    # Limit history_text to prevent Groq 413 error
    # Keeping only the last 3000 characters of history as a safety measure
    max_context_chars = 3000
    if len(history_text) > max_context_chars:
        history_text = "..." + history_text[-max_context_chars:]

    system_instruction = """
    คุณคือ Jarvis ผู้ช่วย AI ส่วนตัว
    ตอบภาษาไทยเท่านั้น
    พูดสุภาพ ลงท้ายครับ
    ตอบสั้น กระชับ เข้าใจง่าย
    ถ้าเป็นความรู้ทั่วไป ให้ตอบจากความรู้ที่มีได้
    ถ้าไม่แน่ใจ ให้บอกว่าไม่แน่ใจ
    ห้ามสร้างตัวเลข ข้อมูลระบบ หรือผลการตรวจสอบที่ไม่มีจริง
    ถ้าไม่เข้าใจคำถาม ให้ถามกลับ
    """
#     system_instruction += personality.get_prompt()
    system_instruction += """
ตอบเฉพาะ JSON เท่านั้น
ใช้บุคลิกตามโหมดปัจจุบัน
ลงท้ายครับ
"""

    prompt = f"""Context:
{history_text}

User:
{user_message}

ตอบ JSON:
{{
 "reply":"ข้อความตอบกลับ",
 "action":null
}}"""

    try:
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            response_format={"type":"json_object"},
            messages=[
                {"role":"system","content":system_instruction},
                {"role":"user","content":prompt}
            ]
        )
        return json.loads(res.choices[0].message.content)
    except Exception as e:
        print("AI Error:", e)
        return {"reply":"ขออภัยครับ ระบบ AI ขัดข้องครับ","action":None}


def _format_developer_result(result):
    """Convert Developer Mode analysis into a compact Telegram-safe reply."""
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

    if len(files) > 20:
        lines.append(f"… และอีก {len(files) - 20} ไฟล์")
    return "\n".join(lines)


def apply_personality_to_action(action_result, history_text=""):
    result = ask_jarvis(
        f"""ข้อมูลจากระบบจริง:
{action_result}

กฎ:
- ห้ามเปลี่ยนตัวเลขหรือข้อมูลระบบ
- ห้ามสร้างข้อมูลใหม่
- ต้องแสดงข้อมูลจริงก่อน
- ค่อยใส่มุกตามหลัง
- ตอบด้วยบุคลิกปัจจุบัน""",
        history_text
    )
    return result.get("reply") or action_result


def worker():
    while True:
        task = task_queue.get()
        try:
            chat_id = task["chat_id"]
            text = task["text"]

            auto_saved = auto_work.save_auto_work(text)
            history = task["history"]
            history_text = "\n".join([f"User:{u}\nJarvis:{b}" for u,b in history])
            db_memory = memory_manager.get_memory(3)

            if db_memory:
                history_text += "\n\n[Previous Memory]\n" + "\n".join(
                    [f"User:{u}\nJarvis:{b}" for u,b in db_memory]
                )

            tool_system_result = None
            tool_system_reply = None
            tool_system_markup = None

            if "เปิดโหมดกวน" in text or "โหมดกวน" in text:
                personality.set_mode("ROAST")
                reply = "เปิดโหมดกวนแล้วครับ 😎"
            elif "กลับโหมดปกติ" in text or "โหมดปกติ" in text:
                personality.set_mode("NORMAL")
                reply = "กลับโหมดปกติแล้วครับ"
            else:
                # Tool System takes priority over Developer Mode for explicit tool commands.
                tool_system_result = _try_tool_system(text, chat_id)
                if tool_system_result is not None and tool_system_result.get("handled"):
                    tool_system_reply = tool_system_result["reply"]
                    tool_system_markup = tool_system_result.get("markup")
                    reply = tool_system_reply
                    auto_saved = "tool_system"
                    result = {"reply": tool_system_reply, "action": None}
                elif developer_mode_router.is_developer_command(text):
                    developer_result = developer_mode_router.execute_developer_command(text)
                    reply = _format_developer_result(developer_result)
                    result = {"reply": reply, "action": None}
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
                elif auto_saved == "duplicate":
                    reply = "งานนี้ผมบันทึกไว้แล้วครับ"
                elif auto_saved is True:
                    reply = "บันทึกงานติดตั้งไฟเบอร์เสร็จแล้วครับ"
                else:
                    if action == "list_jobs":
                        reply = list_jobs()
                    elif action == "search_jobs":
                        area = text.replace("งานที่", "").strip()
                        reply = search_jobs(area)
                    elif action == "pending_jobs":
                        reply = pending_jobs()
                    else:
                        reply = result.get("reply") or "รับทราบครับ"

                    plugin_name = None if auto_saved else PLUGIN_MAP.get(action)
                    if plugin_name:
                        plugin = plugin_loader.get_plugin(plugin_name)
                        if plugin:
                            action_result = plugin.execute(text)
                            reply = action_result

                    reply = reply.replace("ค่ะ","ครับ").replace("คะ","ครับ")

            print("DEBUG CHAT:", chat_id)
            print("DEBUG REPLY:", reply)

            if chat_id:
                if auto_saved == "tool_system" and tool_system_markup is not None:
                    bot.send_message(chat_id, reply, reply_markup=tool_system_markup)
                else:
                    bot.send_message(chat_id, reply, reply_markup=get_main_keyboard())
            try:
                tts.speak(reply)
            except Exception as e:
                print("TTS Error:",e)

            memory_manager.save_memory(text, reply)

        except Exception as e:
            traceback.print_exc()
            _send_admin_alert(traceback.format_exc())
        finally:
            task_queue.task_done()


def get_main_keyboard():
    """สร้าง Telegram Reply Keyboard ภาษาไทย"""
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        telebot.types.KeyboardButton("🤖 Jarvis Menu"),
        telebot.types.KeyboardButton("📋 งานล่าสุด"),
        telebot.types.KeyboardButton("💰 รายจ่าย"),
        telebot.types.KeyboardButton("➕ เพิ่มงาน"),
        telebot.types.KeyboardButton("💵 เพิ่มค่าใช้จ่าย"),
        telebot.types.KeyboardButton("🧠 ความจำ"),
        telebot.types.KeyboardButton("📊 รายงาน"),
        telebot.types.KeyboardButton("🔋 สถานะเครื่อง"),
        telebot.types.KeyboardButton("❓ ช่วยเหลือ"),
    ]
    keyboard.add(*buttons)
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
        bot.edit_message_text(f"❌ Tool ทำงานไม่สำเร็จ\n🧰 {item['tool']}\n{result.error}", call.message.chat.id, call.message.message_id)
        return

    if item["tool"] == "file_write" and isinstance(result.data, dict):
        target = result.data.get("path", "")
        backup = result.data.get("backup_path")
        if str(target).endswith(".py") and backup:
            target_path = Path(__file__).resolve().parent / target
            check = subprocess.run(
                [sys.executable, "-m", "py_compile", str(target_path)],
                cwd=Path(__file__).resolve().parent,
                capture_output=True, text=True, timeout=30,
            )
            if check.returncode != 0:
                try:
                    from tools.file_tool import restore_backup
                    restore_backup(backup, target)
                    bot.edit_message_text(
                        f"⚠️ เขียนไฟล์แล้ว syntax ไม่ผ่าน จึง rollback อัตโนมัติ\n🧰 {item['tool']}\n{check.stderr[-1200:]}",
                        call.message.chat.id, call.message.message_id,
                    )
                except Exception as rollback_error:
                    bot.edit_message_text(
                        f"❌ Syntax ไม่ผ่าน และ rollback ไม่สำเร็จ\n{rollback_error}",
                        call.message.chat.id, call.message.message_id,
                    )
                return

    data = str(result.data)
    if len(data) > 3500:
        data = data[:3500] + "\n… [ตัดข้อความ]"
    bot.edit_message_text(f"✅ อนุมัติและทำงานแล้ว\n🧰 {item['tool']}\n{data}", call.message.chat.id, call.message.message_id)


@bot.message_handler(commands=['start'])
def handle_start(m):
    """ตอบสนองคำสั่ง /start และแสดง Keyboard"""
    if config.TELEGRAM_CHAT_ID and m.chat.id != config.TELEGRAM_CHAT_ID:
        logger.warning("Blocked message from unauthorized chat_id=%s", m.chat.id)
        return

    welcome_message = "สวัสดีครับ! ผมคือ Jarvis ผู้ช่วย AI ของคุณ\n\nเลือกเมนูด้านล่างครับ"
    bot.send_message(m.chat.id, welcome_message, reply_markup=get_main_keyboard())


@bot.message_handler(func=lambda m: True)
def handle(m):
    # Security: drop messages from unknown senders
    if config.TELEGRAM_CHAT_ID and m.chat.id != config.TELEGRAM_CHAT_ID:
        logger.warning("Blocked message from unauthorized chat_id=%s", m.chat.id)
        return
    if m.text:
        # Sanitise input: strip whitespace, enforce max length
        text = m.text.strip()[:2000]
        if not text:
            return
        task_queue.put({
            "chat_id": m.chat.id,
            "text": text,
            "history": memory_manager.get_memory(5)
        })


def voice_worker():
    print("🎤 Voice Mode Started")
    while True:
        try:
            text = voice_stt.listen_and_transcribe()
            if text:
                bot.send_message(config.TELEGRAM_CHAT_ID, f"🎤 {text}")
                task_queue.put({
                    "chat_id": config.TELEGRAM_CHAT_ID,
                    "text": text,
                    "history": memory_manager.get_memory(5)
                })
        except Exception as e:
            print("Voice Error:", e)


if __name__ == "__main__":
    print("Jarvis started")
    threading.Thread(target=worker, daemon=True).start()
    threading.Thread(target=voice_worker, daemon=True).start()
    threading.Thread(target=reminder_worker.run, daemon=True).start()
    uvicorn.run("run:app", host="127.0.0.1", port=8000, reload=False)
