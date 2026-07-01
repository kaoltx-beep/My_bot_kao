import logging
import threading
import json
import telebot
import time
from queue import Queue
from groq import Groq
import device_actions 
import memory_manager
# 1. เพิ่มคำสั่ง import สำหรับทำระบบ Web API
from fastapi import FastAPI
import uvicorn

# 2. กล่องเก็บข้อมูลสุขภาพเรียลไทม์ของ Jarvis
JARVIS_LIVE_STATUS = {
    "last_ai_latency_ms": 0,  # ความเร็ว AI ล่าสุด
    "intent_ok": True,         # สมองยังแยกคำสั่งได้ไหม
    "db_ok": True              # ฐานข้อมูลยังใช้งานได้ดีไหม
}

# (ถัดจากนี้ก็ปล่อยให้เป็นโค้ดเดิมของคุณยาวลงไปจนถึงฟังก์ชัน handle)

# 1. SETUP
logging.basicConfig(level=logging.ERROR, format="%(levelname)s:%(name)s:%(message)s")
API_TOKEN = "8863565201:AAFtQDDIYb5D3hH0VnFQGGkO87Jp3RLfeaY"
GROQ_KEY = "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"

bot = telebot.TeleBot(API_TOKEN)
client = Groq(api_key=GROQ_KEY)
task_queue = Queue()

ACTION_MAP = {
    "open_youtube": device_actions.open_youtube,
    "check_battery": device_actions.check_battery,
}

# 2. HELPER FUNCTIONS
def fallback_intent(text):
    text_lower = text.lower()
    if "แบต" in text_lower or "battery" in text_lower: return "check_battery"
    if "ยูทูป" in text_lower or "youtube" in text_lower: return "open_youtube"
    return None

def ask_jarvis(user_message, history_text=""):
    prompt = f"""คุณคือ Jarvis AI. กฎ: ตอบเป็น JSON เท่านั้น
    {{ "reply": "ข้อความตอบกลับ", "action": "ชื่อคำสั่ง หรือ null" }}
    ประวัติการสนทนา: {history_text}
    คำถาม: {user_message}"""
    
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}]
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {"reply": None, "action": None}

# 3. WORKER
def worker():
    while True:
        task = task_queue.get()
        chat_id, text, history = task["chat_id"], task["text"], task["history"]
        
        history_text = "\n".join([f"User: {u}\nBot: {b}" for u, b in history])
        result = ask_jarvis(text, history_text)
        
        action = result.get("action") or fallback_intent(text)
        reply = result.get("reply") or "รับทราบครับ กำลังดำเนินการให้"

        if action in ACTION_MAP:
            res = ACTION_MAP[action]()
            reply = f"🔧 {res}\n\n{reply}" if res else reply
        
        bot.send_message(chat_id, reply)
        memory_manager.save_memory(text, reply)
        task_queue.task_done()

# 4. TELEGRAM HANDLER
@bot.message_handler(func=lambda message: True)
def handle(message):
    history = memory_manager.get_memory(5)
    task_queue.put({"chat_id": message.chat.id, "text": message.text, "history": history})

# สร้างตัวแปรแอป FastAPI สำหรับทำระบบตรวจชีพจร
app = FastAPI()

@app.get("/pulse")
def pulse():
    is_healthy = JARVIS_LIVE_STATUS["intent_ok"] and JARVIS_LIVE_STATUS["db_ok"]
    return {
        "status": "ok" if is_healthy else "degraded",
        "timestamp": time.time(),
        "intent_ok": JARVIS_LIVE_STATUS["intent_ok"],
        "queue_size": task_queue.qsize() if 'task_queue' in globals() else 0, # เช็กคิวงานจริง 📦
        "ai_latency_ms": JARVIS_LIVE_STATUS["last_ai_latency_ms"],
        "db_ok": JARVIS_LIVE_STATUS["db_ok"]
    }

if __name__ == "__main__":
    # 1. เปิดสวิตช์ให้ Worker ทำงานหลังบ้าน (โค้ดเดิมของคุณ)
    import threading
    threading.Thread(target=worker, daemon=True).start()
    
    # 2. ย้าย Telegram Bot ไปวิ่งในเลนของตัวเอง ไม่ให้บล็อกระบบเว็บ
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    
    print("🤖 Jarvis System & Telegram Bot Ready...")
    
    # 3. สั่งเปิดเครื่องหน้าบ้าน FastAPI ไว้คอยรายงานสุขภาพยาม
    uvicorn.run(app, host="127.0.0.1", port=8000)