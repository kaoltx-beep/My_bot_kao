import subprocess

def speak(text):
    if not text:
        return
    subprocess.run(["termux-tts-speak", text])