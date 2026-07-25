import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MACRODROID_WEBHOOK_URL = os.getenv("MACRODROID_WEBHOOK_URL", "")

LOG_FILE = "data/logs/android_control.jsonl"
