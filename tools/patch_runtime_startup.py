from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "run.py"


def patch() -> None:
    source = TARGET.read_text(encoding="utf-8")
    original = source

    # Ensure the FastAPI application object exists.
    if "app = FastAPI()" not in source:
        marker = '_DASHBOARD_TOKEN = os.getenv("DASHBOARD_TOKEN", "")\n'
        if marker not in source:
            raise SystemExit("หา DASHBOARD_TOKEN marker ไม่พบ")
        source = source.replace(marker, marker + "\napp = FastAPI()\n", 1)

    # Voice is opt-in only. Prevent TTS -> STT self-feedback loops.
    old_voice = '    threading.Thread(target=voice_worker, daemon=True).start()\n'
    new_voice = '    if os.getenv("VOICE_MODE_ENABLED", "0") == "1":\n        threading.Thread(target=voice_worker, daemon=True).start()\n'
    if old_voice in source:
        source = source.replace(old_voice, new_voice, 1)

    # Start Telegram polling in its own daemon thread. The bot handlers then
    # actually receive updates while Uvicorn serves the FastAPI bridge.
    polling_block = '''    def telegram_polling():\n        print("📡 Telegram polling started")\n        bot.infinity_polling(\n            timeout=20,\n            long_polling_timeout=20,\n            allowed_updates=["message", "callback_query"],\n        )\n\n    threading.Thread(target=telegram_polling, daemon=True).start()\n'''
    anchor = '    print("Jarvis started")\n'
    if "Telegram polling started" not in source:
        if anchor not in source:
            raise SystemExit("หา startup marker ไม่พบ")
        source = source.replace(anchor, anchor + polling_block, 1)

    if source == original:
        print("Runtime startup patch already applied")
        return

    backup = ROOT / f"run.py.runtime_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(TARGET, backup)
    TARGET.write_text(source, encoding="utf-8")
    print("✅ Runtime startup patched")
    print(f"🛟 Backup: {backup.name}")


if __name__ == "__main__":
    patch()
