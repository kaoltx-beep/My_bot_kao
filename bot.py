from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import TELEGRAM_TOKEN

try:
    from developer import ask_groq
except Exception:
    ask_groq = None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    if not user_text:
        return

    try:
        if ask_groq:
            reply = ask_groq(user_text)
        else:
            reply = f"คุณพูดว่า: {user_text}"

        if not reply:
            reply = "AI ไม่ได้ส่งข้อความกลับมา"

        await update.message.reply_text(str(reply))

    except Exception as e:
        print(e)
        await update.message.reply_text(f"เกิดข้อผิดพลาด: {e}")


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
