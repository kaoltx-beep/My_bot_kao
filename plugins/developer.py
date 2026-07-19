"""
plugins/developer.py — Jarvis Developer Plugin (Phase A)
Git commands เดิม + READ/ANALYZE ผ่าน dev_agent
"""

import subprocess
import sys
import os

# เพิ่ม project root เข้า path เพื่อ import dev_agent
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import dev_agent

METADATA = {
    "name": "developer",
    "description": "Git tools + Code read/analyze",
    "keywords": [
        # --- Git (เดิม) ---
        "เช็ก git",
        "เชก git",
        "git",
        "ดู branch",
        "branch",
        "github",
        "อัปเดตโค้ด",
        "ส่งขึ้น github",
        "ดู log",
        # --- Code READ (ใหม่) ---
        "อ่านไฟล์",
        "ดูไฟล์",
        "อ่านโค้ด",
        "ดูโค้ด",
        "เปิดไฟล์",
        # --- Code ANALYZE (ใหม่) ---
        "วิเคราะห์",
        "ตรวจสอบโค้ด",
        "ตรวจโค้ด",
        "วิเคราะห์โค้ด",
        "ดูปัญหา",
        # --- LIST (ใหม่) ---
        "ดูไฟล์ทั้งหมด",
        "รายการไฟล์",
        "มีไฟล์อะไร",
    ]
}


# ============================================================
# Git helpers (เดิม — ไม่แตะ)
# ============================================================
def _run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return r.stdout[-3000:] or r.stderr[-3000:]
    except Exception as e:
        return str(e)


def _handle_git(text):
    if "เช็ก git" in text or "เชก git" in text:
        return _run("git status")
    if "ดู branch" in text:
        return _run("git branch")
    if "อัปเดตโค้ด" in text:
        return _run("git pull")
    if "ส่งขึ้น github" in text:
        return _run('git add . && git commit -m "Jarvis update" && git push')
    if "ดู log" in text:
        return _run("tail -50 jarvis.log")
    return None


# ============================================================
# Code helpers (ใหม่ Phase A)
# ============================================================
def _handle_code(text):
    """
    READ: "อ่านไฟล์ memory_manager.py"
    ANALYZE: "วิเคราะห์ plugin_loader.py"
    LIST: "มีไฟล์อะไรบ้าง"
    """

    # LIST ไฟล์
    if any(k in text for k in ["ดูไฟล์ทั้งหมด", "รายการไฟล์", "มีไฟล์อะไร"]):
        return dev_agent.list_project_files()

    # ดึงชื่อไฟล์จากข้อความ
    filename = dev_agent.extract_filename(text)

    # READ
    if any(k in text for k in ["อ่านไฟล์", "ดูไฟล์", "อ่านโค้ด", "ดูโค้ด", "เปิดไฟล์"]):
        if not filename:
            return "❓ ระบุชื่อไฟล์ด้วยครับ เช่น: อ่านไฟล์ memory_manager.py"
        return dev_agent.read_file(filename)

    # ANALYZE
    if any(k in text for k in ["วิเคราะห์", "ตรวจสอบโค้ด", "ตรวจโค้ด", "วิเคราะห์โค้ด", "ดูปัญหา"]):
        if not filename:
            return "❓ ระบุชื่อไฟล์ด้วยครับ เช่น: วิเคราะห์ memory_manager.py"

        # โหลด Groq client จาก config ถ้าทำได้
        groq_client = _get_groq_client()

        # ดึงคำถามเพิ่มเติม (ข้อความหลังชื่อไฟล์)
        question = text.split(filename)[-1].strip()

        return dev_agent.analyze_file(filename, question, groq_client)

    return None


def _get_groq_client():
    """โหลด Groq client จาก config — fail silently ถ้าไม่มี"""
    try:
        from groq import Groq
        import config
        return Groq(api_key=config.GROQ_API_KEY)
    except Exception:
        return None


# ============================================================
# MAIN EXECUTE
# ============================================================
def execute(text=None):
    text = (text or "").strip()

    if not text:
        return None

    # 1. ลอง git ก่อน
    result = _handle_git(text)
    if result is not None:
        return result

    # 2. ลอง code commands
    result = _handle_code(text)
    if result is not None:
        return result

    return None


