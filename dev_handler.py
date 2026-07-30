"""Jarvis Developer Mode handler"""

from pathlib import Path
from code_analyzer import analyze_file


_PROJECT_COMMANDS = (
    "วิเคราะห์โปรเจกต์",
    "ตรวจโปรเจกต์",
    "scan โปรเจกต์",
)
_FILE_KEYWORDS = ("run.py", "plugin", ".py", "แก้", "เพิ่ม", "สร้าง", "error", "ตรวจ")
_MAX_FILES = 50


def handle_dev_request(text, root='.'):
    """รับคำสั่งพัฒนาและวิเคราะห์ไฟล์ที่เกี่ยวข้อง"""
    result = {
        "mode": "developer",
        "request": text,
        "files": []
    }

    root_path = Path(root)
    files = []
    normalized_text = text.lower()

    # Project-level requests should scan Python files instead of requiring
    # the user to name a specific file in the command.
    is_project_request = any(command in normalized_text for command in _PROJECT_COMMANDS)
    if is_project_request:
        files = sorted(root_path.rglob("*.py"))[:_MAX_FILES]
    else:
        for path in root_path.rglob("*.py"):
            if any(keyword in normalized_text for keyword in _FILE_KEYWORDS):
                if path.name.lower() in normalized_text:
                    files.append(path)
            if len(files) >= _MAX_FILES:
                break

    for file in files:
        result["files"].append(analyze_file(file))

    return result
