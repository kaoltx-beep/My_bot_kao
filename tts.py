from __future__ import annotations

import subprocess
import threading


_lock = threading.Lock()
_process: subprocess.Popen | None = None


def speak(text: str):
    """Speak text and keep the TTS process controllable from Telegram.

    This function is defensive: if termux-tts-speak is not available (e.g., on Render),
    it logs and returns without raising. It initializes a local `process` variable
    to avoid UnboundLocalError in exceptional cases.
    """
    global _process
    if not text:
        return

    stop()
    process = None
    try:
        with _lock:
            try:
                _process = subprocess.Popen(["termux-tts-speak", text])
            except FileNotFoundError:
                # termux-tts-speak isn't available on this platform; fail safely
                print("TTS: termux-tts-speak not found on this system; skipping TTS.")
                _process = None
                return
            except Exception as exc:
                print("TTS spawn error:", exc)
                _process = None
                return
            process = _process

        # Wait for the process to finish outside the lock
        if process:
            process.wait()
    except Exception as exc:
        # Ensure any TTS error does not propagate to caller threads
        print("TTS Error:", exc)
    finally:
        with _lock:
            if process is not None and _process is process:
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
