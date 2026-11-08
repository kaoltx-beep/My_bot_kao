"""Jarvis application entrypoint: FastAPI API + optional Telegram polling."""
from __future__ import annotations

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load this project's .env before importing config (required for Termux startup).
load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
import config
import threading

import requests
from fastapi import FastAPI

from ai_gateway import ask_text
from handlers.chat import configure as configure_chat
from handlers.chat import router as chat_router
from handlers.field_ops import router as field_ops_router
from handlers.fastapi import router as system_router
from handlers.line import router as line_router


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="Jarvis API")
app.include_router(system_router)
app.include_router(chat_router)
app.include_router(field_ops_router)
app.include_router(line_router)
try:
    from dashboard.router import router as dashboard_router
    app.include_router(dashboard_router)
except Exception as exc:
    # Dashboard is optional and must never block Telegram/Repair startup.
    logging.getLogger(__name__).warning("Dashboard router disabled: %s", type(exc).__name__)


def _build_tool_system():
    try:
        from core.tool_system import JarvisToolSystem
        return JarvisToolSystem()
    except Exception as exc:
        print("Tool system failed to initialize:", exc)
        return None


# One shared tool system is used by FastAPI and Telegram.
tool_system = _build_tool_system()
configure_chat(ask_text, tool_system=tool_system)


def start_telegram_polling_if_enabled():
    """Start Telegram polling only when explicitly enabled."""
    try:
        import plugin_loader
        plugin_loader.load_plugins()
    except Exception as exc:
        print("Plugin loader failed to initialize:", exc)

    if os.environ.get("TELEGRAM_POLLING_ENABLED", "0") != "1":
        print("Telegram polling disabled by TELEGRAM_POLLING_ENABLED")
        return None

    try:
        import config
        token = getattr(config, "TELEGRAM_TOKEN", None)
        if not token:
            print("TELEGRAM_TOKEN not set — Telegram polling will not start")
            return None

        import telebot
        bot = telebot.TeleBot(token)

        from handlers import register_handlers
        register_handlers(bot, tool_system=tool_system)

        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/deleteWebhook", timeout=10
            )
            try:
                data = resp.json()
            except Exception:
                data = resp.text
            print("Telegram deleteWebhook response:", resp.status_code, data)
        except Exception as exc:
            print("Warning: deleteWebhook failed:", exc)

        def _poll():
            try:
                print("Telegram polling started")
                bot.infinity_polling(
                    timeout=20,
                    long_polling_timeout=20,
                    allowed_updates=["message", "callback_query"],
                )
            except Exception as exc:
                print("Telegram polling stopped with error:", exc)

        threading.Thread(target=_poll, daemon=True).start()
        return bot
    except Exception as exc:
        print("Failed to start Telegram polling:", exc)
        return None


@app.on_event("startup")
def startup() -> None:
    """Run startup logic for both `uvicorn run:app` and `python run.py`."""
    try:
        from field_ops_worker import start_if_enabled
        start_if_enabled()
    except Exception as exc:
        print("Field Ops background sync setup failed:", type(exc).__name__)
    start_telegram_polling_if_enabled()


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("run:app", host="0.0.0.0", port=port, reload=False)
