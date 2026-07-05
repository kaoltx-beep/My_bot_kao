import subprocess
import os
import json
import speech_recognition as sr
from groq import Groq

# 🛠️ ดึงค่าจากไฟล์ config.py ของคุณมาใช้งานโดยตรง
from config import GROQ_API_KEY
client = Groq(api_key=GROQ_API_KEY)

def listen():
    print("🎤 กำลังฟัง... (พูดใส่ไมค์มือถือได้เลย)")
    
    audio_file = "temp_voice.mp3"
    if os.path.exists(audio_file):
        try:
            os.remove(audio_file)
        except:
            pass
        
    subprocess.run(["termux-microphone-record", "-d", "4", "-f", audio_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if not os.path.exists(audio_file) or os.path.getsize(audio_file) == 0:
        return None

    r = sr.Recognizer()
    try:
        with sr.AudioFile(audio_file) as source:
            audio = r.record(source)
        text = r.recognize_google(audio, language="th-TH")
        print("📝 คุณพูด:", text)
        return text
    except Exception as e:
        return None

def ask_jarvis(text):
    prompt = f"""
You are Jarvis AI.
Return JSON only:
{{"reply":"", "action": null}}

User:
{text}
"""
    try:
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}]
        )
        return json.loads(res.choices[0].message.content)
    except Exception as e:
        return {"reply": "ขออภัยครับ ระบบประมวลผลคำตอบขัดข้อง", "action": None}

def speak(text):
    subprocess.run(["termux-tts-speak", text])

def main():
    print("🤖 Jarvis Voice Mode Started (ระบบพร้อมทำงานแล้ว)")

    while True:
        text = listen()

        if not text:
            continue

        result = ask_jarvis(text)
        reply = result.get("reply", "รับทราบครับ")

        print("🤖 Jarvis ตอบ:", reply)
        speak(reply)

if __name__ == "__main__":
    main()