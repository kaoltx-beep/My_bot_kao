from config import TELEGRAM_TOKEN, GROQ_API_KEY

import logging
import threading
import json
import telebot
import time
from queue import Queue
from groq import Groq

import plugin_loader
import intent_router
import memory_manager
import tts

from fastapi import FastAPI
import uvicorn
import os

JARVIS_LIVE_STATUS = {
    "last_ai_latency_ms": 0,
    "intent_ok": True,
    "db_ok": True
}

CURRENT_MODE = "FUN"

PERSONALITY_MODES = {
    "SERIOUS": "พูดสุภาพ ลงท้ายครับ วิเคราะห์ตรงประเด็น",
    "FUN": "เป็นเพื่อนสนิท พูดกวน แซวได้ ใช้คำหยาบตามบริบท แต่ไม่ทำร้ายผู้ใช้",
    "DEVELOPER": "โหมดนักพัฒนา วิเคราะห์ระบบและโค้ดละเอียด"
}

logging.basicConfig(level=logging.ERROR)

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)
task_queue = Queue()

ACTION_MAP = plugin_loader.load_plugins()
print("Loaded plugins:", list(ACTION_MAP.keys()))


def ask_jarvis(user_message, history_text=""):
    plugin_info = plugin_loader.get_plugin_info()

    prompt = f"""
You are Jarvis AI assistant.

Personality Mode: {CURRENT_MODE}
Style:
{PERSONALITY_MODES.get(CURRENT_MODE)}

Available tools:
{json.dumps(plugin_info, ensure_ascii=False)}

Return ONLY valid JSON.
Format:
{{"reply":"", "action": null}}

History:
{history_text}

User:
{user_message}
"""

    try:
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}]
        )

        return json.loads(res.choices[0].message.content)

    except Exception as e:
        print("AI Error:", e)
        return {"reply": "ระบบ AI ขัดข้อง", "action": None}


def worker():
    while True:
        task = task_queue.get()
        reply = ""

        try:
            chat_id = task["chat_id"]
            text = task["text"]
            history = task["history"]

            history_text = "\n".join([f"U:{u} B:{b}" for u, b in history])

            result = ask_jarvis(text, history_text)

            action = result.get("action") or intent_router.classify(text)
            reply = result.get("reply") or "รับทราบ"

            if action in ACTION_MAP:
                reply = ACTION_MAP[action]()

            bot.send_message(chat_id, reply)

            threading.Thread(target=tts.speak, args=(reply,), daemon=True).start()
            memory_manager.save_memory(text, reply)

        except Exception as e:
            print("Worker Error:", e)

        finally:
            task_queue.task_done()


@bot.message_handler(func=lambda m: True)
def handle(m):
    if not m.text:
        return

    task_queue.put({
        "chat_id": m.chat.id,
        "text": m.text,
        "history": memory_manager.get_memory(5)
    })


app = FastAPI()


@app.get("/pulse")
def pulse():
    return {
        "status": "ok",
        "mode": CURRENT_MODE,
        "queue": task_queue.qsize(),
        "plugins": list(ACTION_MAP.keys()),
        "time": time.time()
    }


if __name__ == "__main__":
    threading.Thread(target=worker, daemon=True).start()
    threading.Thread(target=bot.infinity_polling, daemon=True).start()

    print("Jarvis started")

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
