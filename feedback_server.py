import telebot
from groq import Groq
from gtts import gTTS
import sqlite3
import config
import os

client = Groq(api_key=config.GROQ_API_KEY)
bot = telebot.TeleBot(config.TELEGRAM_TOKEN)

conn = sqlite3.connect("chat_history.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS history (chat_id INTEGER, role TEXT, content TEXT)")
conn.commit()

@bot.message_handler(func=lambda message: True)
def chat(message):
    chat_id = message.chat.id
    c.execute("INSERT INTO history (chat_id, role, content) VALUES (?, ?, ?)", (chat_id, "user", message.text))
    
    history = [{"role": "system", "content": "คุณคือผู้ช่วย AI ชื่อไอริณ ตอบสุภาพ อ่อนหวาน ลงท้ายด้วย 'ค่ะ' เสมอ"}]
    c.execute("SELECT role, content FROM history WHERE chat_id=? ORDER BY rowid DESC LIMIT 8", (chat_id,))
    for role, content in c.fetchall()[::-1]:
        history.append({"role": role, "content": content})

    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=history,
            max_tokens=200,
            temperature=0.6
        )
        reply = resp.choices[0].message.content
        
        # ส่งข้อความเป็นตัวอักษร
        bot.reply_to(message, reply)
        
        # แปลงเป็นเสียงและส่งไฟล์
        tts = gTTS(text=reply, lang='th')
        tts.save("voice.mp3")
        with open("voice.mp3", "rb") as audio:
            bot.send_voice(chat_id, audio)
            
    except Exception as e:
        bot.reply_to(message, f"ไอริณขอโทษค่ะ เกิดข้อผิดพลาด: {e}")

bot.infinity_polling()
