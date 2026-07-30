import platform
import subprocess


def speak(text):
    if not text:
        return

    system = platform.system()

    if system == "Windows":
        escaped = text.replace("'", "''")
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Speak('{escaped}')"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            check=False,
        )
        return

    if system == "Linux":
        subprocess.run(["termux-tts-speak", text], check=False)
        return

    raise RuntimeError(f"Unsupported TTS platform: {system}")
