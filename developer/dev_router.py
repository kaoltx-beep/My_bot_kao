"""Jarvis Developer Mode command router.
Safe bridge layer. Existing bot flow remains unchanged.
"""

from developer.dev_handler import handler
from developer.code_analyzer import analyzer
from developer.patch_generator import patch_generator
from developer.test_runner import runner
from developer.backup_manager import backup_manager


def handle_developer_request(text):
    text = text.lower()

    if "สถานะ developer" in text or "developer mode" in text:
        return handler.status()

    if "วิเคราะห์ระบบ" in text or "ตรวจโค้ด" in text:
        return analyzer.analyze(["run.py"])

    if "เพิ่มฟังก์ชั่น" in text or "แก้โค้ด" in text:
        return patch_generator.generate(text)

    if "ทดสอบระบบ" in text:
        return runner.run("jarvis")

    if "backup" in text:
        return backup_manager.create_backup_record("jarvis")

    return None
