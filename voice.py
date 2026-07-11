import subprocess
import os
import speech_recognition as sr

def listen_voice():
    audio_file = "temp_voice.m4a"
    if os.path.exists(audio_file):
        try: os.remove(audio_file)
        except: pass
        
    print("🎤 กำลังฟัง... (พูดใส่ไมค์มือถือได้เลย)")
    subprocess.run(["termux-microphone-record", "-d", "4", audio_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if not os.path.exists(audio_file) or os.path.getsize(audio_file) == 0:
        return None

    r = sr.Recognizer()
    try:
        with sr.AudioFile(audio_file) as source:
            audio = r.record(source)
        text = r.recognize_google(audio, language="th-TH")
        print("📝 คุณพูด:", text)
        return text
    except:
        return None

def speak_voice(text):
    if text:
        subprocess.run(["termux-tts-speak", text])

