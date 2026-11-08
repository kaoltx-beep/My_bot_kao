import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core import approval
from handlers import telegram


class FakeBot:
    def __init__(self):
        self.message_handler_fn = None
        self.callback_handler_fn = None
        self.sent = []
        self.edited = []
        self.answers = []

    def message_handler(self, **_kwargs):
        return lambda fn: setattr(self, "message_handler_fn", fn) or fn

    def callback_query_handler(self, **_kwargs):
        return lambda fn: setattr(self, "callback_handler_fn", fn) or fn

    def send_message(self, chat_id, text, reply_markup=None):
        self.sent.append((chat_id, text, reply_markup))
        return SimpleNamespace(message_id=700 + len(self.sent))

    def edit_message_text(self, text, chat_id, message_id):
        self.edited.append((text, chat_id, message_id))

    def answer_callback_query(self, callback_id, text):
        self.answers.append((callback_id, text))


class FakeToolSystem:
    def __init__(self):
        self.call = SimpleNamespace(tool_name="mcp:read_status", params={"detail": "brief"})
        self.tool = SimpleNamespace(metadata=SimpleNamespace(risk_level="high", require_approval=True))
        self.registry = SimpleNamespace(get=lambda name: self.tool if name == "mcp:read_status" else None)
        self.executions = []

    def parse(self, _text):
        return self.call

    def execute(self, name, params, **kwargs):
        self.executions.append((name, params, kwargs))
        return SimpleNamespace(success=True, data={"result": 7}, error=None)


class TelegramApprovalFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store_patch = patch.object(approval, "STORE", Path(self.tmp.name) / "approvals.json")
        self.store_patch.start()
        self.config = types.ModuleType("config")
        self.config.TELEGRAM_CHAT_ID = 123
        self.config_patch = patch.dict(sys.modules, {"config": self.config})
        self.config_patch.start()
        self.telebot = types.ModuleType("telebot")
        class InlineKeyboardMarkup:
            def __init__(self, **_kwargs):
                self.buttons = []
            def add(self, *buttons):
                self.buttons.extend(buttons)
        self.telebot.types = SimpleNamespace(
            InlineKeyboardMarkup=InlineKeyboardMarkup,
            InlineKeyboardButton=lambda text, callback_data: (text, callback_data),
        )
        self.telebot_patch = patch.dict(sys.modules, {"telebot": self.telebot})
        self.telebot_patch.start()
        self.bot = FakeBot()
        self.tools = FakeToolSystem()
        self.allowed_chat_patch = patch.object(telegram, "_allowed_chat_id", return_value=123)
        self.allowed_chat_patch.start()
        telegram.register_handlers(self.bot, self.tools)

    def tearDown(self):
        self.allowed_chat_patch.stop()
        self.telebot_patch.stop()
        self.config_patch.stop()
        self.store_patch.stop()
        self.tmp.cleanup()

    def make_message(self, user_id=456, chat_id=123, text="read status"):
        return SimpleNamespace(
            text=text,
            chat=SimpleNamespace(id=chat_id),
            from_user=SimpleNamespace(id=user_id),
        )

    def make_callback(self, approval_id, user_id=456, chat_id=123, message_id=701, action="approve"):
        return SimpleNamespace(
            id="callback-1",
            data=f"jarvis_approval:{action}:{approval_id}",
            message=SimpleNamespace(
                chat=SimpleNamespace(id=chat_id),
                message_id=message_id,
            ),
            from_user=SimpleNamespace(id=user_id),
        )

    def test_high_risk_message_requests_approval_without_execution(self):
        message = self.make_message()
        self.assertEqual(telegram._allowed_chat_id(), 123)
        self.assertEqual(int(message.chat.id), 123)
        self.assertEqual(int(message.from_user.id), 456)
        self.assertIsNotNone(self.bot.message_handler_fn)
        self.bot.message_handler_fn(message)
        self.assertEqual(self.tools.executions, [])
        self.assertEqual(len(self.bot.sent), 1)
        approval_id = self.bot.sent[0][2].buttons[0][1].split(":")[-1]
        item = approval.get(approval_id)
        self.assertEqual(item["chat_id"], 123)
        self.assertEqual(item["user_id"], 456)
        self.assertEqual(item["message_id"], 701)

    def test_wrong_user_cannot_approve_but_owner_can(self):
        self.bot.message_handler_fn(self.make_message())
        approval_id = self.bot.sent[0][2].buttons[0][1].split(":")[-1]
        self.bot.callback_handler_fn(self.make_callback(approval_id, user_id=999))
        self.assertEqual(self.tools.executions, [])

        self.bot.callback_handler_fn(self.make_callback(approval_id))
        self.assertEqual(len(self.tools.executions), 1)
        name, params, kwargs = self.tools.executions[0]
        self.assertEqual(name, "mcp:read_status")
        self.assertEqual(params, {"detail": "brief"})
        self.assertTrue(kwargs["approved"])
        self.assertTrue(kwargs["approval_grant"])

    def test_callback_from_different_message_cannot_approve(self):
        self.bot.message_handler_fn(self.make_message())
        approval_id = self.bot.sent[0][2].buttons[0][1].split(":")[-1]
        self.bot.callback_handler_fn(self.make_callback(approval_id, message_id=999))
        self.assertEqual(self.tools.executions, [])

    def test_reject_consumes_request_without_execution(self):
        self.bot.message_handler_fn(self.make_message())
        approval_id = self.bot.sent[0][2].buttons[0][1].split(":")[-1]
        self.bot.callback_handler_fn(self.make_callback(approval_id, action="reject"))
        self.assertEqual(self.tools.executions, [])
        self.assertIn("ยกเลิกคำขอ", self.bot.edited[0][0])

    def test_unapproved_chat_is_ignored(self):
        self.bot.message_handler_fn(self.make_message(chat_id=999))
        self.assertEqual(self.bot.sent, [])
        self.assertEqual(self.tools.executions, [])


if __name__ == "__main__":
    unittest.main()
