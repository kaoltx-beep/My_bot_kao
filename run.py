import threading
import time
import logging
import json
from queue import Queue
import telebot
from groq import Groq

import config
import device_actions
import plugin_loader
plugin_loader.load_plugins()
import personality

PLUGIN_MAP = {
    "check_battery": "battery",
    "open_youtube": "youtube",
}

import memory_manager
import tts

from fastapi import FastAPI
import uvicorn

JARVIS_LIVE_STATUS = {
    "last_ai_latency_ms": 0,
    "intent_ok": True,
    "db_ok": True
}

logging.basicConfig(level=logging.ERROR)

bot = telebot.TeleBot(config.TELEGRAM_TOKEN)
client = Groq(api_key=config.GROQ_API_KEY)

task_queue = Queue()

ACTION_MAP = {
    "open_youtube": device_actions.open_youtube,
    "check_battery": device_actions.check_battery,
}


def fallback_intent(text):
    text = text.lower()

    if "แบต" in text or "battery" in text:
        return "check_battery"

    if "youtube" in text or "ยูทูป" in text:
        return "open_youtube"

    return None


def ask_jarvis(user_message, history_text=""):
    system_instruction = personality.get_prompt()
    system_instruction += """

กฎเพิ่มเติม:
- ตอบเฉพาะ JSON ตามรูปแบบที่กำหนดเท่านั้น
- ลงท้ายครับ
"""

    prompt = f"""Context:
{history_text}

User:
{user_message}

ตอบกลับเป็น JSON รูปแบบนี้เท่านั้น:
{{
  "reply": "ข้อความตอบกลับ",
  "action": null
}}"""

    try:
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ]
        )
        return json.loads(res.choices[0].message.content)
    except Exception as e:
        print("AI Error:", e)
        return {"reply": "ขออภัยครับ ระบบ AI ขัดข้องครับ", "action": None}


def worker():
    while True:
        task = task_queue.get()
        reply = ""

        try:
            chat_id = task["chat_id"]
            text = task["text"]
            history = task["history"]

            # เปลี่ยนโหมดบุคลิก
            if "เปิดโหมดกวน" in text or "โหมดกวน" in text:
                personality.set_mode("ROAST")
                reply = "เปิดโหมดกวนแล้วครับ 😎"
            elif "กลับโหมดปกติ" in text or "โหมดปกติ" in text:
                personality.set_mode("NORMAL")
                reply = "กลับโหมดปกติแล้วครับ"
            else:
                history_text = "\n".join([f"User:{u}\nJarvis:{b}" for u, b in history])
                result = ask_jarvis(text, history_text)

                action = result.get("action") or fallback_intent(text)
                reply = result.get("reply") or "รับทราบครับ"

                reply = reply.replace("ค่ะ", "ครับ").replace("คะ", "ครับ")

                if action in PLUGIN_MAP:
                    try:
                        plugin = plugin_loader.get_plugin(PLUGIN_MAP[action])
                        if plugin:
                            reply = plugin.execute()
                    except Exception as e:
                        print("PLUGIN Error:", e)

            bot.send_message(chat_id, reply)

            try:
                tts.speak(reply)
            except Exception as e:
                print("TTS Error:", e)

            try:
                memory_manager.save_memory(text, reply)
            except Exception as e:
                print("Memory Error:", e)

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
        "queue": task_queue.qsize(),
        "time": time.time()
    }


if __name__ == "__main__":
    threading.Thread(target=worker, daemon=True).start()
    threading.Thread(target=bot.infinity_polling, daemon=True).start()

    print("Jarvis started")
    uvicorn.run(app, host="127.0.0.1", port=8000)
