2026-07-17

Move AI to ai_engine.py

Memory v1 Complete

OpenClaw Pairing Success


2026-07-17
Implement context limiting in `run.py` to mitigate Groq 413 (Request Entity Too Large) error.


2026-07-17
Implement Dashboard Authentication for `/pulse` and `/status` routes.


2026-11-24
Restore `config.TELEGRAM_CHAT_ID` from the `TELEGRAM_CHAT_ID` environment variable with a safe default of `0`, preserving fail-closed Telegram access control and fixing the missing configuration attribute reported by CI.