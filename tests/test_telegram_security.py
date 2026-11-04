import unittest
from types import SimpleNamespace
from unittest.mock import patch

from handlers.telegram import register_handlers


class FakeBot:
    def __init__(self):
        self.handler = None
        self.sent = []

    def message_handler(self, **kwargs):
        def decorator(fn):
            self.handler = fn
            return fn
        return decorator

    def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))


def make_message(chat_id, text="hello"):
    return SimpleNamespace(chat=SimpleNamespace(id=chat_id), text=text)


class TelegramAccessControlTests(unittest.TestCase):
    def test_unconfigured_chat_id_denies_everyone(self):
        bot = FakeBot()
        with patch("config.TELEGRAM_CHAT_ID", 0), patch("handlers.telegram.process_message") as process:
            register_handlers(bot)
            bot.handler(make_message(123))
        process.assert_not_called()
        self.assertEqual(bot.sent, [])

    def test_wrong_chat_is_ignored(self):
        bot = FakeBot()
        with patch("config.TELEGRAM_CHAT_ID", 123), patch("handlers.telegram.process_message") as process:
            register_handlers(bot)
            bot.handler(make_message(456))
        process.assert_not_called()
        self.assertEqual(bot.sent, [])

    def test_allowed_chat_reaches_chat_pipeline(self):
        bot = FakeBot()
        with patch("config.TELEGRAM_CHAT_ID", 123), patch(
            "handlers.telegram.process_message",
            return_value={"status": "success", "reply": "ok"},
        ) as process:
            register_handlers(bot)
            bot.handler(make_message(123))
        process.assert_called_once_with("hello")
        self.assertEqual(bot.sent, [(123, "ok")])


if __name__ == "__main__":
    unittest.main()
