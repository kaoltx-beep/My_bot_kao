import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MACRODROID_WEBHOOK_URL = os.getenv("MACRODROID_WEBHOOK_URL")

LOG_FILE = "data/logs/app.log"

TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", 0))
