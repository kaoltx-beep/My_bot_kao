"""Jarvis application entrypoint: FastAPI API + optional Telegram polling."""
from __future__ import annotations

import os
import threading
from typing import Any

from fastapi import FastAPI

from handlers.chat import configure as configure_chat
from handlers.chat import router as chat_router
from handlers.fastapi import router as system_router

app = FastAPI(title="Jarvis API")
app.include_router(system_router)
app.include_router(chat_router)


# Keep the current AI implementation behind the handler boundary. This makes
# /chat independently testable and lets the AI backend be replaced later
# without moving FastAPI transport code back into run.py.
def _chat_callback(prompt: str) -> dict[str, Any]:
    try:
        import g4f

        response = g4f.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
        )
        return {"status": "success", "reply": response}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


configure_chat(_chat_callback)


def start_telegram_polling_if_enabled():
    """Start Telegram polling only when explicitly enabled.

    n8n is the intended Telegram ingress for the Render deployment, so polling
    defaults to disabled to avoid competing getUpdates consumers.
    """
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
        try:
            from core.tool_system import JarvisToolSystem
            tool_system = JarvisToolSystem()
        except Exception as exc:
            print("Tool system failed to initialize:", exc)
            tool_system = None

        register_handlers(bot, tool_system=tool_system)

        try:
            import requests
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
    start_telegram_polling_if_enabled()


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("run:app", host="0.0.0.0", port=port, reload=False)
