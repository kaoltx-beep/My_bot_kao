import subprocess
import os
import time
from groq import Groq
import config

client = Groq(api_key=config.GROQ_API_KEY)


def record_audio():
    filename = f"/data/data/com.termux/files/home/voice_{int(time.time())}.m4a"

    subprocess.run([
        "termux-microphone-record",
        "-f",
        filename,
        "-l",
        "5",
        "-r",
        "16000",
        "-c",
        "1",
        "-b",
        "64000"
    ])

    time.sleep(5)

    return filename


def convert_audio(filename):
    wav = filename.replace(".m4a", ".wav")

    subprocess.run([
        "ffmpeg",
        "-y",
        "-i",
        filename,
        "-ar",
        "16000",
        "-ac",
        "1",
        wav
    ])

    return wav


def speech_to_text(filename):
    try:
        with open(filename, "rb") as audio:
            result = client.audio.transcriptions.create(
                file=audio,
                model="whisper-large-v3",
                language="th"
            )

        return result.text

    except Exception as e:
        print("STT Error:", e)
        return None


def listen():
    m4a = record_audio()

    if not os.path.exists(m4a):
        return None

    wav = convert_audio(m4a)

    if not os.path.exists(wav):
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
