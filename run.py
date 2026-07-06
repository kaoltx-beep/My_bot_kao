from config import TELEGRAM_TOKEN, GROQ_API_KEY

import logging
import threading
import json
import telebot
import time
from queue import Queue
from groq import Groq

import device_actions
import memory_manager
import tts

from fastapi import FastAPI
import uvicorn
import os

# ------------------
# STATUS
# ------------------
JARVIS_LIVE_STATUS = {
    "last_ai_latency_ms": 0,
    "intent_ok": True,
    "db_ok": True
}

logging.basicConfig(level=logging.ERROR)

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

task_queue = Queue()

ACTION_MAP = {
    "open_youtube": device_actions.open_youtube,
    "check_battery": device_actions.check_battery,
}


# ------------------
# fallback intent
# ------------------
def fallback_intent(text):
    text = text.lower()

    if "แบต" in text or "battery" in text:
        return "check_battery"

    if "youtube" in text or "ยูทูป" in text:
        return "open_youtube"

    return None


# ------------------
# AI
# ------------------
def ask_jarvis(user_message, history_text=""):
    prompt = f"""
You are Jarvis AI. Return ONLY valid JSON.

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
        return {"reply": "ขออภัย ระบบ AI ขัดข้อง", "action": None}


# ------------------
# worker
# ------------------
def worker():
    while True:
        task = task_queue.get()

        reply = ""   # 🔥 กันพัง

        try:
            chat_id = task["chat_id"]
            text = task["text"]
            history = task["history"]

            history_text = "\n".join([f"U:{u} B:{b}" for u, b in history])

            result = ask_jarvis(text, history_text)

            action = result.get("action") or fallback_intent(text)
            reply = result.get("reply") or "รับทราบ"

            if action in ACTION_MAP:
                try:
                    reply = ACTION_MAP[action]()
                except Exception as e:
                    print("ACTION Error:", e)

            bot.send_message(chat_id, reply)

            # 🔊 TTS กันพัง
            try:
                tts.speak(reply)
            except Exception as e:
                print("TTS Error:", e)

            # 🧠 memory กันพัง
            try:
                memory_manager.save_memory(text, reply)
            except Exception as e:
                print("Memory Error:", e)

        except Exception as e:
            print("Worker Error:", e)
            print("DEBUG reply =", reply)

        finally:
            task_queue.task_done()


# ------------------
# telegram
# ------------------
@bot.message_handler(func=lambda m: True)
def handle(m):
    if not m.text:
        return

    task_queue.put({
        "chat_id": m.chat.id,
        "text": m.text,
        "history": memory_manager.get_memory(5)
    })


# ------------------
# fastapi
# ------------------
app = FastAPI()

@app.get("/pulse")
def pulse():
    return {
        "status": "ok",
        "queue": task_queue.qsize(),
        "time": time.time()
    }


# ------------------
# start
# ------------------
if __name__ == "__main__":
    threading.Thread(target=worker, daemon=True).start()
    threading.Thread(target=bot.infinity_polling, daemon=True).start()

    print("Jarvis started")

    # Get port from environment or default to 8000
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
