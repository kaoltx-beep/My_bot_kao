#!/usr/bin/env python3
"""ทดสอบ Developer Mode แบบ end-to-end"""

import subprocess
import tempfile
import re

# init git
subprocess.run(["git", "init"], capture_output=True)
subprocess.run(["git", "config", "user.email", "test@jarvis.bot"])
subprocess.run(["git", "config", "user.name", "Jarvis Test"])

from developer import create_developer_mode
from developer.telegram_handler import TelegramCommandHandler

dev = create_developer_mode(allowed_dirs=[".", "/tmp"])

handler = TelegramCommandHandler(
    router=dev.router,
    agent=dev.agent,
    patcher=dev.patcher,
    git=dev.git,
    sessions=dev.sessions,
    logger=dev.logger
)

print("=" * 60)
print("🧪 END-TO-END TEST")
print("=" * 60)

print("\n1️⃣ Analyze")
result = handler.handle_command(
    "/dev_analyze developer/dev_logger.py",
    "test",
    "1"
)
print(result["message"][:500])

print("\n2️⃣ Generate")
result = handler.handle_command(
    '/dev_generate test_new.py "สร้างฟังก์ชัน hello"',
    "test",
    "1"
)
print(result["message"][:600])

m = re.search(r'([a-f0-9]{8})', result["message"])

if m:
    sid = m.group(1)
    print("\n3️⃣ Approve")
    result = handler.handle_command(
        f"/dev_approve {sid}",
        "admin",
        "1"
    )
    print(result["message"][:500])

print("\n4️⃣ Status")
result = handler.handle_command(
    "/dev_status",
    "test",
    "1"
)
print(result["message"])

print("\n✅ TEST COMPLETE")
