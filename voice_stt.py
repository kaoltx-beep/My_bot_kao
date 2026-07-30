import subprocess
import os
import time
from groq import Groq
import config


client = Groq(
    api_key=config.GROQ_API_KEY,
    timeout=30.0
)

HOME = "/data/data/com.termux/files/home"


def record_audio():
    filename = f"{HOME}/voice_{int(time.time())}.m4a"
    subprocess.run([
        "termux-microphone-record",
        "-f", filename,
        "-l", "3",
        "-r", "16000",
        "-c", "1",
        "-b", "64000"
    ], check=True)

    for _ in range(10):
        if os.path.exists(filename) and os.path.getsize(filename) > 20000:
            break
        time.sleep(1)

    time.sleep(2)
    return filename


def convert_audio(filename):
    wav = filename.replace(".m4a", ".wav")

    if not os.path.exists(filename):
        return None

    result = subprocess.run([
        "ffmpeg",
        "-y",
        "-i", filename,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        wav
    ])

    if result.returncode != 0:
        return None

    return wav


def speech_to_text(filename):
    try:
        with open(filename, "rb") as audio:
            result = client.audio.transcriptions.create(
                file=("voice.wav", audio, "audio/wav"),
                model="whisper-large-v3-turbo",
                language="th"
            )

        return result.text.strip()
    except Exception as e:
        print("STT Error:", repr(e))
        return None


def listen():
    m4a = record_audio()
    wav = convert_audio(m4a)
    if not wav:
        print("❌ แปลงไฟล์เสียงไม่ได้")
        return None

    print("ไฟล์:", wav)
    print("ขนาด:", os.path.getsize(wav))

    text = speech_to_text(wav)
    if not text:
        return None

    if len(text.strip()) < 2:
        return None

    return text


# Compatibility API used by run.py / voice worker.
def listen_and_transcribe():
    return listen()


if __name__ == "__main__":
    print("🎤 กำลังฟัง...")
    text = listen()
    if text:
        print("Voice:", text)
    else:
        print("❌ ไม่ได้ยินเสียง")
