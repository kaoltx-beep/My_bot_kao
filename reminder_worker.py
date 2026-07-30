import sqlite3
import time
from datetime import datetime

DB = "reminder.db"


def get_due_reminders():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    c.execute(
        """
        SELECT id, text, remind_time
        FROM reminders
        WHERE remind_time <= ?
        AND status = 'waiting'
        """,
        (now,)
    )

    rows = c.fetchall()
    conn.close()

    return rows


def mark_done(reminder_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        "UPDATE reminders SET status='done' WHERE id=?",
        (reminder_id,)
    )

    conn.commit()
    conn.close()


def worker(send_message):
    print("⏰ Reminder Worker Started")

    while True:
        try:
            reminders = get_due_reminders()

            if reminders:
                print("Reminder Found:", reminders)

            for reminder_id, text, remind_time in reminders:
                message = f"⏰ แจ้งเตือนครับ\n{text}\nเวลา {remind_time}"
                print("Sending:", message)
                send_message(message)
                mark_done(reminder_id)

        except Exception as e:
            print("Reminder Worker Error:", e)

        time.sleep(30)


# Compatibility API used by run.py. Uses the configured Telegram bot when available.
def run():
    try:
        import config
        import telebot
        bot = telebot.TeleBot(config.TELEGRAM_TOKEN)
        chat_id = config.TELEGRAM_CHAT_ID

        def send_message(message):
            if chat_id:
                bot.send_message(chat_id, message)

        worker(send_message)
    except Exception as e:
        print("Reminder run error:", e)
