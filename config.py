import os

SECRETS_DIR = os.path.expanduser('~/.secrets')
SERVICE_ACCOUNT_FILE = os.path.join(SECRETS_DIR, 'service_account.json')
SHEETS_CONFIG_FILE = os.path.join(SECRETS_DIR, 'sheets_config.json')

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

MACRODROID_WEBHOOK_URL = os.getenv("MACRODROID_WEBHOOK_URL")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL")
GROQ_VISION_MODEL = os.environ.get("GROQ_VISION_MODEL")

# Optional Cloudflare Workers AI text provider (does not replace Groq vision).
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_AI_MODEL = os.environ.get("CLOUDFLARE_AI_MODEL", "@cf/meta/llama-3.1-8b-instruct")
AI_PROVIDER = os.environ.get("AI_PROVIDER", "groq")
