import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

try:
    from mcp import Client
    from mcp.server import MCPServer
except ImportError:
    Client = None
    MCPServer = None

from core import approval
from core.executor import ToolExecutor
from core.registry import ToolRegistry
from handlers import telegram
from mcp_tool_adapter import MCPToolAdapter


class FakeBot:
    def __init__(self):
        self.message_handler_fn = None
        self.callback_handler_fn = None
        self.sent = []
        self.edited = []

    def message_handler(self, **_kwargs):
        return lambda fn: setattr(self, "message_handler_fn", fn) or fn

    def callback_query_handler(self, **_kwargs):
        return lambda fn: setattr(self, "callback_handler_fn", fn) or fn

    def send_message(self, chat_id, text, reply_markup=None):
        self.sent.append((chat_id, text, reply_markup))
        return SimpleNamespace(message_id=701)

    def answer_callback_query(self, *_args):
        return None

    def edit_message_text(self, text, chat_id, message_id):
        self.edited.append((text, chat_id, message_id))


class MCPBackedToolSystem:
    def __init__(self, adapter):
        self.registry = ToolRegistry()
        self.registry.register(adapter)
        self.executor = ToolExecutor(self.registry)

    def parse(self, _text):
        return SimpleNamespace(tool_name="mcp:read_status", params={})

    def execute(self, name, params, **kwargs):
        return self.executor.execute(name, params, **kwargs)


@unittest.skipIf(Client is None, "MCP SDK integration runs in isolated environment")
class TelegramToMCPApprovalIntegrationTests(unittest.TestCase):
    def test_telegram_owner_approval_executes_exact_in_memory_mcp_tool(self):
        server = MCPServer("Jarvis Telegram approval integration test")

        @server.tool()
        def read_status() -> int:
            """Read a harmless status value without changing state."""
            return 7

        adapter = MCPToolAdapter(
            server_url="http://127.0.0.1:8000/mcp",
            tool_name="read_status",
            allowed_tools={"read_status"},
            timeout_seconds=3,
        )
        tool_system = MCPBackedToolSystem(adapter)
        bot = FakeBot()

        config = types.ModuleType("config")
        config.TELEGRAM_CHAT_ID = 123
        telebot = types.ModuleType("telebot")

        class InlineKeyboardMarkup:
            def __init__(self, **_kwargs):
                self.buttons = []

            def add(self, *buttons):
                self.buttons.extend(buttons)

        telebot.types = SimpleNamespace(
            InlineKeyboardMarkup=InlineKeyboardMarkup,
            InlineKeyboardButton=lambda text, callback_data: (text, callback_data),
        )

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(approval, "STORE", Path(tmp) / "approvals.json"):
                with patch.dict(sys.modules, {"config": config, "telebot": telebot}):
                    with patch(
                        "mcp.Client",
                        side_effect=lambda _url: Client(server, raise_exceptions=True),
                    ):
                        telegram.register_handlers(bot, tool_system)
                        message = SimpleNamespace(
                            text="read status",
                            chat=SimpleNamespace(id=123),
                            from_user=SimpleNamespace(id=456),
                        )
                        bot.message_handler_fn(message)

                        self.assertEqual(len(bot.sent), 1)
                        approval_id = bot.sent[0][2].buttons[0][1].split(":")[-1]
                        callback = SimpleNamespace(
                            id="callback-1",
                            data=f"jarvis_approval:approve:{approval_id}",
                            message=SimpleNamespace(
                                chat=SimpleNamespace(id=123),
                                message_id=701,
                            ),
                            from_user=SimpleNamespace(id=456),
                        )
                        bot.callback_handler_fn(callback)

        self.assertEqual(len(bot.edited), 1)
        self.assertIn("อนุมัติและทำงานแล้ว", bot.edited[0][0])
        self.assertIn("{'result': 7}", bot.edited[0][0])


if __name__ == "__main__":
    unittest.main()
