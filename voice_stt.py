import subprocess
import os
import time
from groq import Groq
import config

client = Groq(api_key=config.GROQ_API_KEY)

HOME = "/data/data/com.termux/files/home"


def record_audio():
    filename = f"{HOME}/voice_{int(time.time())}.m4a"

    # stop old recording first
    subprocess.run(["termux-microphone-record", "-q"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)

    p = subprocess.Popen([
        "termux-microphone-record",
        "-f", filename,
        "-l", "5",
        "-r", "16000",
        "-c", "1",
        "-b", "64000"
    ])

    time.sleep(6)
    subprocess.run(["termux-microphone-record", "-q"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    p.wait(timeout=3)

    return filename


def convert_audio(filename):
    wav = filename.replace(".m4a", ".wav")

    if not os.path.exists(filename) or os.path.getsize(filename) < 20000:
        return None

    result = subprocess.run([
        "ffmpeg", "-y",
        "-i", filename,
        "-ar", "16000",
        "-ac", "1",
        wav
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if result.returncode != 0:
        return None

    return wav


def speech_to_text(filename):
    try:
        with open(filename, "rb") as audio:
            result = client.audio.transcriptions.create(
                file=audio,
                model="whisper-large-v3",
                language="th"
            )
        return result.text.strip()
    except Exception as e:
        print("STT Error:", e)
        return None


def listen():
    m4a = record_audio()
    wav = convert_audio(m4a)

    if not wav:
        print("❌ ไฟล์เสียงเสีย")
        return None

    print("ไฟล์:", wav)
    print("ขนาด:", os.path.getsize(wav))

    return speech_to_text(wav)


if __name__ == "__main__":
    print("🎤 กำลังฟัง...")
    text = listen()
    if text:
        print("Voice:", text)
    else:
        print("❌ ไม่ได้ยินเสียง")
