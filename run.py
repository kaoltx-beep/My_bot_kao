"""Entrypoint for Render: FastAPI app + background Telegram polling + plugin loading."""
from __future__ import annotations

import os
import threading
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"status": "ok"}


def start_telegram_polling_if_enabled():
    """Start Telegram polling in a background daemon thread if TELEGRAM_TOKEN is set.

    Does not import modules that auto-start polling; loads plugins via plugin_loader only.
    """
    try:
        import config
        # plugin loader is safe to import and will only import plugin modules (no polling)
        import plugin_loader
        plugin_loader.load_plugins()
    except Exception as exc:
        print("Plugin loader failed to initialize:", exc)

    enabled = os.environ.get("TELEGRAM_POLLING_ENABLED", "1")
    if enabled != "1":
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

        def _poll():
            try:
                print("📡 Telegram polling started")
                bot.infinity_polling(
                    timeout=20,
                    long_polling_timeout=20,
                    allowed_updates=["message", "callback_query"],
                )
            except Exception as exc:
                print("Telegram polling stopped with error:", exc)

        t = threading.Thread(target=_poll, daemon=True)
        t.start()
        return bot
    except Exception as exc:
        print("Failed to start Telegram polling:", exc)
        return None


if __name__ == "__main__":
    # Start polling in background (if configured), then serve FastAPI with uvicorn
    start_telegram_polling_if_enabled()

    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("run:app", host="0.0.0.0", port=port, reload=False)
