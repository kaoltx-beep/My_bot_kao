import os
import shutil
from datetime import datetime


def backup_file(path):
    if not os.path.exists(path):
        return None

    backup = f"{path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(path, backup)
    return backup


def apply_patch(path, new_content):
    backup = backup_file(path)

    if not backup:
        return "❌ ไม่พบไฟล์"

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return f"✅ แก้ไขสำเร็จ\nBackup: {backup}"
