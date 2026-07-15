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
plugin_loader.load_plugins()
import personality
import smart_router  # noqa: F401 – stub kept for compat
import auto_work

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
from fastapi import FastAPI, Header, HTTPException
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

            db_memory = memory_manager.get_memory(5)

            if db_memory:
                history_text += "\n\n" + "\n".join(
                    [f"User:{u}\nJarvis:{b}" for u,b in db_memory]
                )

            if "เปิดโหมดกวน" in text or "โหมดกวน" in text:
                personality.set_mode("ROAST")
                reply = "เปิดโหมดกวนแล้วครับ 😎"
            elif "กลับโหมดปกติ" in text or "โหมดปกติ" in text:
                personality.set_mode("NORMAL")
                reply = "กลับโหมดปกติแล้วครับ"
            else:
                result = ask_jarvis(text, history_text)
                action = intent_router.classify(text) or fallback_intent(text) or result.get("action")

                if isinstance(action, list):
                    action = action[0] if action else None
                if auto_saved == "duplicate":
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

                        if plugin_name == "news":
                            reply = action_result
                        else:
                            reply = action_result

                reply = reply.replace("ค่ะ","ครับ").replace("คะ","ครับ")

            print("DEBUG CHAT:", chat_id)
            print("DEBUG REPLY:", reply)

            if chat_id:
                bot.send_message(chat_id, reply)
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
            text = voice_stt.listen()

            if text:
                print("Voice:", text)

                task_queue.put({
                    "chat_id": config.TELEGRAM_CHAT_ID,
                    "text": text,
                    "history": memory_manager.get_memory(5)
                })

            time.sleep(1)

        except Exception as e:
            print("Voice Error:", e)
            time.sleep(3)



def send_reminder_message(message):
    try:
        bot.send_message(config.TELEGRAM_CHAT_ID, message)
    except Exception as e:
        print("Reminder Send Error:", e)

app = FastAPI()
app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")

@app.get("/pulse", dependencies=[])
def pulse():
    return {"status": "ok", "queue": task_queue.qsize(), "time": time.time()}


@app.get("/status", dependencies=[])
def status():
    try:
        jobs = list_jobs()
    except Exception as e:
        jobs = str(e)

    try:
        expenses = monthly_summary()
    except Exception as e:
        expenses = str(e)

    return {
        "jarvis": "online",
        "queue": task_queue.qsize(),
        "jobs": jobs,
        "expenses": expenses,
        "time": time.time()
    }




@app.post("/webhook/feedback")
def webhook_feedback(data: dict):
    print("MacroDroid Feedback:", data)
    return {"status":"ok"}


if __name__ == "__main__":
    threading.Thread(target=worker, daemon=True).start()
    threading.Thread(target=reminder_worker.worker, args=(send_reminder_message,), daemon=True).start()
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
  # threading.Thread(target=voice_worker, daemon=True).start()
    print("Jarvis started")
    uvicorn.run(app, host="127.0.0.1", port=8000)
