from __future__ import annotations

import subprocess
import threading


_lock = threading.Lock()
_process: subprocess.Popen | None = None


def speak(text: str):
    """Speak text and keep the TTS process controllable from Telegram."""
    global _process
    if not text:
        return

    stop()
    try:
        with _lock:
            _process = subprocess.Popen(["termux-tts-speak", text])
            process = _process
        process.wait()
    except Exception as exc:
        print("TTS Error:", exc)
    finally:
        with _lock:
            if _process is process:
                _process = None


def stop() -> bool:
    """Stop the currently running TTS process, if any."""
    global _process
    with _lock:
        process = _process
        _process = None

    if process is None:
        return False

    try:
        if process.poll() is None:
            process.terminate()
        return True
    except Exception as exc:
        print("TTS Stop Error:", exc)
        return False
