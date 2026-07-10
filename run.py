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
import plugin_router
plugin_loader.load_plugins()
import personality

PLUGIN_MAP = {
    "check_battery": "battery",
    "open_youtube": "youtube",
    "news": "news",
}

import memory_manager
import tts
import voice_stt

from fastapi import FastAPI
import uvicorn

logging.basicConfig(level=logging.ERROR)

bot = telebot.TeleBot(config.TELEGRAM_TOKEN)
client = Groq(api_key=config.GROQ_API_KEY)

task_queue = Queue()


def fallback_intent(text):
    text = text.lower()
    if "แบต" in text or "battery" in text:
        return "check_battery"
    if "youtube" in text or "ยูทูป" in text:
        return "open_youtube"

    if "ข่าว" in text or "news" in text:
        return "news"

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
            history = task["history"]
            history_text = "\n".join([f"User:{u}\nJarvis:{b}" for u,b in history])

            if "เปิดโหมดกวน" in text or "โหมดกวน" in text:
                personality.set_mode("ROAST")
                reply = "เปิดโหมดกวนแล้วครับ 😎"
            elif "กลับโหมดปกติ" in text or "โหมดปกติ" in text:
                personality.set_mode("NORMAL")
                reply = "กลับโหมดปกติแล้วครับ"
            else:
                result = ask_jarvis(text, history_text)
                action = result.get("action") or fallback_intent(text)
                reply = result.get("reply") or "รับทราบครับ"

                plugin_name = plugin_router.find_plugin(text)

                if plugin_name:
                    plugin = plugin_loader.get_plugin(plugin_name)

                    if plugin:
                        action_result = plugin.execute()
                        reply = apply_personality_to_action(action_result, history_text)

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
            print("Worker Error:",e)
        finally:
            task_queue.task_done()


@bot.message_handler(func=lambda m: True)
def handle(m):
    if m.text:
        task_queue.put({
            "chat_id":m.chat.id,
            "text":m.text,
            "history":memory_manager.get_memory(5)
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

app = FastAPI()

@app.get("/pulse")
def pulse():
    return {"status":"ok","queue":task_queue.qsize(),"time":time.time()}


if __name__ == "__main__":
    threading.Thread(target=worker, daemon=True).start()
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
  # threading.Thread(target=voice_worker, daemon=True).start()
    print("Jarvis started")
    uvicorn.run(app, host="127.0.0.1", port=8000)
