"""
dev_agent.py — Jarvis Developer Agent (Phase A)
ความสามารถ: READ + ANALYZE ไฟล์เท่านั้น
ยังไม่มี: PATCH, APPLY, RUN
"""

import os
import re

# ============================================================
# CONFIG
# ============================================================
PROJECT_ROOT = os.path.expanduser("~/My_bot_kao")
MAX_FILE_SIZE = 6000   # chars — ประมาณ 1500 token ปลอดภัยกับ Groq
ALLOWED_EXTENSIONS = {".py", ".txt", ".md", ".json", ".sh", ".cfg", ".ini"}

# ============================================================
# SECURITY
# ============================================================
def _safe_path(filename: str):
    """
    ป้องกัน path traversal เช่น ../../../etc/passwd
    คืน absolute path ถ้าปลอดภัย หรือ None ถ้าไม่ปลอดภัย
    """
    # ไม่อนุญาต path separator ในชื่อไฟล์
    if "/" in filename or "\\" in filename:
        return None, "❌ ชื่อไฟล์ไม่อนุญาตให้มี / หรือ \\"

    # ตรวจ extension
    _, ext = os.path.splitext(filename)
    if ext not in ALLOWED_EXTENSIONS:
        return None, f"❌ ไม่รองรับไฟล์ประเภท '{ext}' — รองรับเฉพาะ: {', '.join(ALLOWED_EXTENSIONS)}"

    full_path = os.path.join(PROJECT_ROOT, filename)

    # Double-check ว่า path อยู่ใน project root จริง
    if not os.path.realpath(full_path).startswith(os.path.realpath(PROJECT_ROOT)):
        return None, "❌ ไฟล์อยู่นอก project ไม่อนุญาต"

    return full_path, None


# ============================================================
# READ FILE
# ============================================================
def read_file(filename: str) -> str:
    """
    อ่านไฟล์จาก project root
    คืนข้อความพร้อมแสดงใน Telegram
    """
    path, err = _safe_path(filename)
    if err:
        return err

    if not os.path.exists(path):
        # แสดงไฟล์ที่มีจริงช่วย user
        available = _list_py_files()
        return f"❌ ไม่พบไฟล์: {filename}\n\n📁 ไฟล์ที่มีในโปรเจกต์:\n{available}"

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        size = len(content)
        truncated = False

        if size > MAX_FILE_SIZE:
            content = content[:MAX_FILE_SIZE]
            truncated = True

        lines = content.count("\n") + 1
        result = f"📄 *{filename}* ({lines} บรรทัด"
        if truncated:
            result += f", แสดง {MAX_FILE_SIZE} chars แรกจาก {size} chars"
        result += ")\n"
        result += f"```python\n{content}\n```"

        return result

    except Exception as e:
        return f"❌ อ่านไฟล์ไม่ได้: {e}"


# ============================================================
# ANALYZE FILE
# ============================================================
def analyze_file(filename: str, question: str = "", groq_client=None) -> str:
    """
    วิเคราะห์ไฟล์ด้วย AI
    ถ้าไม่มี groq_client → คืนเนื้อหาไฟล์เปล่าๆ
    """
    path, err = _safe_path(filename)
    if err:
        return err

    if not os.path.exists(path):
        available = _list_py_files()
        return f"❌ ไม่พบไฟล์: {filename}\n\n📁 ไฟล์ที่มี:\n{available}"

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return f"❌ อ่านไฟล์ไม่ได้: {e}"

    # ถ้าไม่มี AI client → คืน raw content
    if not groq_client:
        return read_file(filename)

    # ตัดถ้ายาวเกิน
    code_for_ai = content[:MAX_FILE_SIZE]
    if len(content) > MAX_FILE_SIZE:
        code_for_ai += "\n# ... [โค้ดส่วนที่เหลือถูกตัดออก]"

    user_question = question.strip() or "วิเคราะห์โค้ดโดยรวม: บอกหน้าที่, จุดเสี่ยง, และข้อเสนอแนะ"

    prompt = f"""คุณคือ Senior Python Developer ช่วยวิเคราะห์โค้ดนี้

ไฟล์: {filename}
```python
{code_for_ai}
```

คำถาม: {user_question}

ตอบเป็นภาษาไทย กระชับ ชัดเจน แบ่งเป็นหัวข้อ:
1. หน้าที่ของไฟล์นี้
2. จุดเสี่ยง/ปัญหาที่พบ
3. ข้อเสนอแนะ"""

    try:
        res = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.3
        )
        analysis = res.choices[0].message.content
        return f"🔍 วิเคราะห์ *{filename}*:\n\n{analysis}"

    except Exception as e:
        # AI ล้ม → คืนโค้ดดิบแทน
        return f"⚠️ AI วิเคราะห์ไม่ได้ ({e})\n\n{read_file(filename)}"


# ============================================================
# LIST FILES (helper)
# ============================================================
def _list_py_files() -> str:
    """แสดงรายการไฟล์ .py ในโปรเจกต์"""
    try:
        files = []
        for f in sorted(os.listdir(PROJECT_ROOT)):
            if f.endswith(".py"):
                files.append(f"  • {f}")

        plugin_dir = os.path.join(PROJECT_ROOT, "plugins")
        if os.path.exists(plugin_dir):
            for f in sorted(os.listdir(plugin_dir)):
                if f.endswith(".py") and not f.startswith("__"):
                    files.append(f"  • plugins/{f}")

        return "\n".join(files) if files else "  (ไม่พบไฟล์)"
    except Exception:
        return "  (อ่าน directory ไม่ได้)"


def list_project_files() -> str:
    """Public function — แสดงไฟล์โปรเจกต์ทั้งหมด"""
    files = _list_py_files()
    return f"📁 ไฟล์ในโปรเจกต์ {PROJECT_ROOT}:\n{files}"


# ============================================================
# EXTRACT FILENAME FROM TEXT (helper สำหรับ plugin)
# ============================================================
def extract_filename(text: str) -> str | None:
    """
    ดึงชื่อไฟล์จากข้อความ
    เช่น "วิเคราะห์ memory_manager.py" → "memory_manager.py"
    """
    # หา pattern .py filename
    match = re.search(r'[\w_]+\.(?:py|txt|md|json|sh|cfg|ini)', text)
    if match:
        return match.group(0)
    return None

