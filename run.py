"""Render entrypoint: FastAPI + Telegram polling + AI chat endpoint."""
from __future__ import annotations

import os
import threading
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"status": "ok"}


class ChatRequest(BaseModel):
    prompt: str


@app.post("/chat")
def chat_with_ai(request: ChatRequest):
    try:
        import g4f
        response = g4f.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": request.prompt}],
        )
        return {"status": "success", "reply": response}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def start_telegram_polling_if_enabled():
    try:
        import plugin_loader
        plugin_loader.load_plugins()
    except Exception as exc:
        print("Plugin loader failed to initialize:", exc)

    if os.environ.get("TELEGRAM_POLLING_ENABLED", "1") != "1":
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

        try:
            from handlers import register_handlers
            try:
                from core.tool_system import JarvisToolSystem
                tool_system = JarvisToolSystem()
            except Exception:
                tool_system = None
            register_handlers(bot, tool_system=tool_system)
        except Exception as exc:
            print("Warning: failed to import/register handlers:", exc)

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


if __name__ == "__main__":
    start_telegram_polling_if_enabled()

    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("run:app", host="0.0.0.0", port=port, reload=False)
