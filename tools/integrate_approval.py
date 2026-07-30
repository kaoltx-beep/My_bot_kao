from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "run.py"

IMPORT_MARK = "from core.approval import create as create_approval, consume as consume_approval"
CALLBACK_MARK = "@bot.callback_query_handler(func=lambda call: call.data.startswith(\"tool_approval:\"))"
HELPER_MARK = "def _try_tool_system(text, chat_id=None):"
BRANCH_MARK = "tool_system_result = _try_tool_system(text, chat_id)"

IMPORT_BLOCK = "from core.approval import create as create_approval, consume as consume_approval\n"

HELPER_BLOCK = '''\n\ndef _try_tool_system(text, chat_id=None):\n    """V1 approval-aware bridge. Low-risk tools execute; high-risk tools pause for approval."""\n    try:\n        call = tool_system.parse(text)\n        if call is None:\n            return None\n\n        tool = tool_system.registry.get(call.tool_name)\n        if tool is None:\n            return None\n\n        if tool.metadata.risk_level in {"high", "critical"}:\n            if chat_id is None:\n                return None\n            approval_id = create_approval(call.tool_name, call.params, int(chat_id))\n            markup = telebot.types.InlineKeyboardMarkup(row_width=2)\n            markup.add(\n                telebot.types.InlineKeyboardButton("✅ อนุมัติ", callback_data=f"tool_approval:approve:{approval_id}"),\n                telebot.types.InlineKeyboardButton("❌ ยกเลิก", callback_data=f"tool_approval:reject:{approval_id}"),\n            )\n            return {\n                "handled": True,\n                "reply": f"🛡 ต้องอนุมัติก่อน\\nTool: {call.tool_name}\\nคำขอ: {call.params}\\nรหัส: {approval_id}",\n                "markup": markup,\n            }\n\n        if tool.metadata.risk_level not in {"low", "medium"}:\n            return None\n\n        result = tool_system.execute(call.tool_name, call.params)\n        if not result.success:\n            return {"handled": True, "reply": f"🛠 Tool {call.tool_name} ไม่สำเร็จ: {result.error}", "markup": None}\n\n        data = result.data\n        if isinstance(data, list):\n            data = "\\n".join(" | ".join(map(str, row)) if isinstance(row, (list, tuple)) else str(row) for row in data)\n        data = str(data)\n        max_chars = 3500\n        if len(data) > max_chars:\n            data = data[:max_chars] + "\\n… [ตัดข้อความเพื่อป้องกัน Telegram message too long]"\n        return {"handled": True, "reply": f"🧰 {call.tool_name}\\n{data}", "markup": None}\n    except Exception as exc:\n        print("Tool System Error:", exc)\n        return None\n'''

CALLBACK_BLOCK = '''\n\n@bot.callback_query_handler(func=lambda call: call.data.startswith("tool_approval:"))\ndef handle_tool_approval(call):\n    if config.TELEGRAM_CHAT_ID and call.message and call.message.chat.id != config.TELEGRAM_CHAT_ID:\n        bot.answer_callback_query(call.id, "ไม่ได้รับอนุญาต")\n        return\n\n    parts = call.data.split(":", 2)\n    if len(parts) != 3:\n        bot.answer_callback_query(call.id, "ข้อมูลอนุมัติไม่ถูกต้อง")\n        return\n\n    action, approval_id = parts[1], parts[2]\n    status = "approved" if action == "approve" else "rejected" if action == "reject" else None\n    if status is None:\n        bot.answer_callback_query(call.id, "คำสั่งไม่ถูกต้อง")\n        return\n\n    item = consume_approval(approval_id, status)\n    if item is None:\n        bot.answer_callback_query(call.id, "คำขอนี้ถูกใช้ไปแล้วหรือหมดอายุ")\n        return\n\n    if status == "rejected":\n        bot.answer_callback_query(call.id, "ยกเลิกแล้ว")\n        bot.edit_message_text("❌ ยกเลิก Tool: " + item["tool"], call.message.chat.id, call.message.message_id)\n        return\n\n    result = tool_system.execute(item["tool"], item["params"], approved=True)\n    bot.answer_callback_query(call.id, "อนุมัติแล้ว")\n    if result.success:\n        data = str(result.data)\n        if len(data) > 3500:\n            data = data[:3500] + "\\n… [ตัดข้อความ]"\n        bot.edit_message_text(f"✅ อนุมัติและทำงานแล้ว\\n🧰 {item['tool']}\\n{data}", call.message.chat.id, call.message.message_id)\n    else:\n        bot.edit_message_text(f"❌ Tool ทำงานไม่สำเร็จ\\n🧰 {item['tool']}\\n{result.error}", call.message.chat.id, call.message.message_id)\n'''

OLD_BRANCH = '''            else:\n                tool_system_reply = _try_tool_system(text)\n                if tool_system_reply is not None:\n                    reply = tool_system_reply\n                    auto_saved = "tool_system"\n                    result = {"reply": tool_system_reply, "action": None}\n                else:\n                    result = ask_jarvis(text, history_text)\n'''
NEW_BRANCH = '''            else:\n                tool_system_result = _try_tool_system(text, chat_id)\n                if tool_system_result is not None and tool_system_result.get("handled"):\n                    reply = tool_system_result["reply"]\n                    tool_system_markup = tool_system_result.get("markup")\n                    auto_saved = "tool_system"\n                    result = {"reply": reply, "action": None}\n                else:\n                    tool_system_markup = None\n                    result = ask_jarvis(text, history_text)\n'''

OLD_SEND = '''            if chat_id:\n                bot.send_message(chat_id, reply, reply_markup=get_main_keyboard())\n'''
NEW_SEND = '''            if chat_id:\n                if auto_saved == "tool_system" and 'tool_system_markup' in locals() and tool_system_markup is not None:\n                    bot.send_message(chat_id, reply, reply_markup=tool_system_markup)\n                else:\n                    bot.send_message(chat_id, reply, reply_markup=get_main_keyboard())\n'''


def integrate() -> None:
    source = TARGET.read_text(encoding="utf-8")
    original = source

    if IMPORT_MARK not in source:
        needle = "from core.tool_system import JarvisToolSystem\n"
        if needle not in source:
            raise SystemExit("หา Tool System import ไม่พบ")
        source = source.replace(needle, needle + IMPORT_BLOCK, 1)

    if HELPER_MARK not in source:
        start = source.find("\ndef _try_tool_system(text):")
        if start < 0:
            raise SystemExit("หา Tool bridge ไม่พบ")
        end = source.find("\ndef _send_admin_alert(error_text: str):", start)
        if end < 0:
            raise SystemExit("หาจุดจบ Tool bridge ไม่พบ")
        source = source[:start] + HELPER_BLOCK + source[end:]

    if CALLBACK_MARK not in source:
        needle = "@bot.message_handler(func=lambda m: True)\n"
        if needle not in source:
            raise SystemExit("หา message handler ไม่พบ")
        source = source.replace(needle, CALLBACK_BLOCK + "\n" + needle, 1)

    if BRANCH_MARK not in source:
        if OLD_BRANCH not in source:
            raise SystemExit("หา worker Tool branch ไม่พบ")
        source = source.replace(OLD_BRANCH, NEW_BRANCH, 1)

    if OLD_SEND in source and "tool_system_markup" not in source[source.find(OLD_SEND)-300:source.find(OLD_SEND)]:
        source = source.replace(OLD_SEND, NEW_SEND, 1)

    if source == original:
        print("Approval flow ติดตั้งอยู่แล้ว")
        return

    backup = ROOT / f"run.py.approval_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(TARGET, backup)
    TARGET.write_text(source, encoding="utf-8")
    print("✅ Approval flow installed")
    print(f"🛟 Backup: {backup.name}")


if __name__ == "__main__":
    integrate()
