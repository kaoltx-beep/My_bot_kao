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


def make_message(chat_id, text="hello", user_id=None):
    return SimpleNamespace(chat=SimpleNamespace(id=chat_id, type="private"), from_user=SimpleNamespace(id=user_id if user_id is not None else chat_id), text=text)


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

    def test_myid_returns_sender_id_only_in_allowed_chat(self):
        bot = FakeBot()
        with patch("config.TELEGRAM_CHAT_ID", 123):
            register_handlers(bot)
            bot.handler(make_message(123, "/myid", user_id=987654))
        self.assertEqual(bot.sent, [(123, "Telegram User ID: 987654")])

    def test_authorized_developer_command_receives_sender_id(self):
        bot = FakeBot()
        with patch("config.TELEGRAM_CHAT_ID", 123), patch("handlers.telegram.developer_mode.is_authorized_admin", return_value=True), patch(
            "handlers.telegram.execute_developer_command",
            return_value={"files": [{"status": "ok", "file": "status ok"}]},
        ) as execute:
            register_handlers(bot)
            bot.handler(make_message(123, "สถานะระบบ", user_id=987654))
        execute.assert_called_once_with("สถานะระบบ", actor_id=987654)
        self.assertEqual(bot.sent, [(123, "status ok")])

    def test_developer_command_denied_without_admin_allowlist(self):
        bot = FakeBot()
        with patch("config.TELEGRAM_CHAT_ID", 123), patch.dict("os.environ", {"JARVIS_DEVELOPER_ADMIN_IDS": ""}), patch("handlers.telegram.process_message") as process:
            register_handlers(bot)
            bot.handler(make_message(123, "สถานะระบบ", user_id=123))
        process.assert_not_called()
        self.assertIn("ไม่มีสิทธิ์", bot.sent[0][1])


if __name__ == "__main__":
    unittest.main()
