"""Jarvis application entrypoint: FastAPI API + optional Telegram polling."""
from __future__ import annotations

import os
import threading
from typing import Any

import requests
from fastapi import FastAPI

from handlers.chat import configure as configure_chat
from handlers.chat import router as chat_router
from handlers.fastapi import router as system_router

app = FastAPI(title="Jarvis API")
app.include_router(system_router)
app.include_router(chat_router)


# Single AI gateway. g4f/Copilot/HAR is intentionally not used here.
# Groq exposes an OpenAI-compatible Chat Completions endpoint.
def _chat_callback(prompt: str, memory: list[Any] | None = None) -> dict[str, Any]:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return {
            "status": "error",
            "reply": "",
            "message": "GROQ_API_KEY is not configured",
        }

    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "คุณคือ Jarvis ผู้ช่วย AI ส่วนตัว ตอบภาษาเดียวกับผู้ใช้ "
                "ตอบกระชับ ชัดเจน และใช้บริบทความจำเมื่อมีให้"
            ),
        }
    ]

    if memory:
        context = "\n".join(
            f"ผู้ใช้: {row[0]}\nJarvis: {row[1]}" for row in memory
        )
        messages.append({
            "role": "system",
            "content": "บริบทความจำล่าสุดของ Jarvis:\n" + context,
        })

    messages.append({"role": "user", "content": prompt})

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.2,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        return {
            "status": "success",
            "reply": reply,
            "model": model,
        }
    except requests.HTTPError as exc:
        detail = exc.response.text[:1000] if exc.response is not None else str(exc)
        return {
            "status": "error",
            "reply": "",
            "message": f"AI gateway HTTP error: {detail}",
        }
    except Exception as exc:
        return {
            "status": "error",
            "reply": "",
            "message": f"AI gateway error: {exc}",
        }


def _build_tool_system():
    try:
        from core.tool_system import JarvisToolSystem
        return JarvisToolSystem()
    except Exception as exc:
        print("Tool system failed to initialize:", exc)
        return None


# One shared tool system is used by FastAPI and Telegram.
tool_system = _build_tool_system()
configure_chat(_chat_callback, tool_system=tool_system)


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
    start_telegram_polling_if_enabled()


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("run:app", host="0.0.0.0", port=port, reload=False)
