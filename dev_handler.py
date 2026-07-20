"""Jarvis Developer Mode handler"""

from pathlib import Path
from code_analyzer import analyze_file


def handle_dev_request(text, root='.'):
    """รับคำสั่งพัฒนาและวิเคราะห์ไฟล์ที่เกี่ยวข้อง"""
    result = {
        "mode": "developer",
        "request": text,
        "files": []
    }

    keywords = ["run.py", "plugin", ".py", "แก้", "เพิ่ม", "สร้าง"]
    files = []

    for path in Path(root).rglob("*.py"):
        if any(k in text for k in keywords) and path.name in text:
            files.append(str(path))

    for file in files:
        result["files"].append(analyze_file(file))

    return result
