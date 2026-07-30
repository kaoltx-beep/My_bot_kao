import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # Environment variables still work even when python-dotenv is unavailable.
    pass

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MACRODROID_WEBHOOK_URL = os.getenv("MACRODROID_WEBHOOK_URL", "")

LOG_FILE = os.path.join("data", "logs", "android_control.jsonl")
