"""Safe patch preparation for Jarvis Developer Mode"""

from pathlib import Path


def create_patch(file_path, new_content):
    """สร้างไฟล์ patch สำรองก่อนแก้จริง"""
    path = Path(file_path)
    backup = path.with_suffix(path.suffix + ".backup")

    if path.exists():
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    return {
        "file": str(path),
        "backup": str(backup),
        "ready": True,
        "content": new_content
    }
