from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "run.py"

IMPORT_MARK = "from core.tool_system import JarvisToolSystem"
INSTANCE_MARK = "tool_system = JarvisToolSystem()"
HELPER_MARK = "def _try_tool_system(text):"
BRANCH_MARK = "tool_system_reply = _try_tool_system(text)"
TOOL_BRANCH_MARK = 'if auto_saved == "tool_system":'

IMPORT_BLOCK = "from core.tool_system import JarvisToolSystem\n"
INSTANCE_BLOCK = "tool_system = JarvisToolSystem()\n"
HELPER_BLOCK = '''\n\ndef _try_tool_system(text):\n    """V1 bridge: parse parameters and execute low-risk tools only."""\n    try:\n        call = tool_system.parse(text)\n        if call is None:\n            return None\n\n        tool = tool_system.registry.get(call.tool_name)\n        if tool is None:\n            return None\n        if tool.metadata.risk_level != "low":\n            return None\n\n        result = tool_system.execute(call.tool_name, call.params)\n        if not result.success:\n            return f"🛠 Tool {call.tool_name} ไม่สำเร็จ: {result.error}"\n\n        data = result.data\n        if isinstance(data, list):\n            data = "\\n".join(" | ".join(map(str, row)) if isinstance(row, (list, tuple)) else str(row) for row in data)\n        return f"🧰 {call.tool_name}\\n{data}"\n    except Exception as exc:\n        print("Tool System Error:", exc)\n        return None\n'''

OLD_BRANCH = '''            else:\n                result = ask_jarvis(text, history_text)\n'''
NEW_BRANCH = '''            else:\n                tool_system_reply = _try_tool_system(text)\n                if tool_system_reply is not None:\n                    reply = tool_system_reply\n                    auto_saved = "tool_system"\n                    result = {"reply": tool_system_reply, "action": None}\n                else:\n                    result = ask_jarvis(text, history_text)\n'''

OLD_AUTOSAVE_BRANCH = '''                if auto_saved == "duplicate":\n                    reply = "งานนี้ผมบันทึกไว้แล้วครับ"\n                elif auto_saved is True:\n                    reply = "บันทึกงานติดตั้งไฟเบอร์เสร็จแล้วครับ"\n                else:\n'''
NEW_AUTOSAVE_BRANCH = '''                if auto_saved == "tool_system":\n                    reply = tool_system_reply\n                elif auto_saved == "duplicate":\n                    reply = "งานนี้ผมบันทึกไว้แล้วครับ"\n                elif auto_saved is True:\n                    reply = "บันทึกงานติดตั้งไฟเบอร์เสร็จแล้วครับ"\n                else:\n'''


def integrate() -> None:
    if not TARGET.exists():
        raise SystemExit("ไม่พบ run.py")

    source = TARGET.read_text(encoding="utf-8")
    original = source

    if IMPORT_MARK not in source:
        needle = "import auto_work\n"
        if needle not in source:
            raise SystemExit("หา import auto_work ไม่พบ: หยุดเพื่อความปลอดภัย")
        source = source.replace(needle, needle + IMPORT_BLOCK, 1)

    if INSTANCE_MARK not in source:
        needle = "task_queue = Queue()\n"
        if needle not in source:
            raise SystemExit("หา task_queue ไม่พบ: หยุดเพื่อความปลอดภัย")
        source = source.replace(needle, needle + INSTANCE_BLOCK, 1)

    if HELPER_MARK not in source:
        needle = "def _send_admin_alert(error_text: str):\n"
        if needle not in source:
            raise SystemExit("หาจุดแทรก Tool bridge ไม่พบ: หยุดเพื่อความปลอดภัย")
        source = source.replace(needle, HELPER_BLOCK + "\n" + needle, 1)

    if BRANCH_MARK not in source:
        if OLD_BRANCH not in source:
            raise SystemExit("หา worker branch ไม่พบ: หยุดเพื่อความปลอดภัย")
        source = source.replace(OLD_BRANCH, NEW_BRANCH, 1)

    if TOOL_BRANCH_MARK not in source:
        if OLD_AUTOSAVE_BRANCH not in source:
            raise SystemExit("หา auto_saved branch ไม่พบ: หยุดเพื่อความปลอดภัย")
        source = source.replace(OLD_AUTOSAVE_BRANCH, NEW_AUTOSAVE_BRANCH, 1)

    if source == original:
        print("Tool System bridge ติดตั้งอยู่แล้ว")
        return

    backup = ROOT / f"run.py.toolbridge_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(TARGET, backup)
    TARGET.write_text(source, encoding="utf-8")
    print("✅ Tool System bridge installed")
    print(f"🛟 Backup: {backup.name}")


if __name__ == "__main__":
    integrate()
