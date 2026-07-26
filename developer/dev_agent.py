import os
import json
import ast
from groq import Groq
from config import GROQ_API_KEY

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
READABLE_EXT = {".py", ".txt", ".md", ".json"}
PROTECTED    = {"run.py", "config.py", ".env", "__pycache__"}
MAX_LINES    = 100
MODEL        = "llama-3.1-8b-instant"


def _validate(code):
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, str(e)


def _list_files():
    result = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "backups")]
        for f in files:
            ext = os.path.splitext(f)[1]
            if ext in READABLE_EXT and not any(p in f for p in PROTECTED):
                rel = os.path.relpath(os.path.join(root, f), PROJECT_ROOT)
                result.append(rel)
    return sorted(result)


def _read_snippet(rel_path):
    full = os.path.join(PROJECT_ROOT, rel_path)
    try:
        with open(full, encoding="utf-8") as f:
            lines = f.readlines()
        out = "".join(lines[:MAX_LINES])
        if len(lines) > MAX_LINES:
            out += f"\n...(ตัดที่ {MAX_LINES}/{len(lines)})"
        return out
    except Exception as e:
        return f"[อ่านไม่ได้: {e}]"


def _pick_files(request, all_files):
    req = request.lower()
    priority, fallback = [], []
    for f in all_files:
        words = f.lower().replace("/", " ").replace("_", " ").split()
        if any(w in req for w in words):
            priority.append(f)
        elif f.endswith(".py"):
            fallback.append(f)
    return (priority if priority else fallback[:5])[:6]


def _extract_json(text):
    try:
        return json.loads(text)
    except Exception:
        pass
    s = text.find("{")
    e = text.rfind("}")
    if s != -1 and e > s:
        try:
            return json.loads(text[s:e+1])
        except Exception:
            pass
    return None


def analyze(user_request):
    try:
        client    = Groq(api_key=GROQ_API_KEY)
        all_files = _list_files()
        relevant  = _pick_files(user_request, all_files)

        file_ctx = ""
        for rel in relevant:
            file_ctx += f"\n### {rel}\n{_read_snippet(rel)}\n"

        # ── Call 1: แผนงาน (JSON เล็ก ไม่มีโค้ด) ────────────────────────
        r1 = client.chat.completions.create(
            model=MODEL,
            max_tokens=300,
            messages=[
                {"role": "system", "content": (
                    "ตอบ JSON บรรทัดเดียว ห้ามพูดเพิ่ม\n"
                    'format: {"target_file":"path","action":"add_function","function_name":"name","description":"text"}\n'
                    "ไฟล์ที่ห้ามเลือก: run.py, config.py, __init__.py, dev_router.py, dev_agent.py, dev_patcher.py, plugin_loader.py, plugin_router.py\n"
                    "ถ้าคำสั่งเป็นการสร้าง plugin ใหม่ อนุญาตสร้างไฟล์ใหม่ใน plugins/ ได้\n"
                    "ห้ามแก้ไฟล์ protected เช่น run.py config.py dev_agent.py"
                )},
                {"role": "user", "content": (
                    f"คำสั่ง: {user_request}\n"
                    f"ไฟล์: {', '.join(all_files)}\n"
                    f"{file_ctx}"
                )},
            ]
        )

        plan = _extract_json(r1.choices[0].message.content.strip())
        if not plan:
            return {"error": f"Call1 ไม่ได้ JSON: {r1.choices[0].message.content[:120]}"}

        target      = plan.get("target_file", "")
        action      = plan.get("action", "add_function")
        func_name   = plan.get("function_name", "new_func")
        description = plan.get("description", user_request)

        if not target:
            return {"error": "Call1 ไม่ระบุ target_file"}

        # ตรวจ PROTECTED — ห้ามแก้ไฟล์สำคัญ
        protected_files = {"run.py", "config.py", ".env", "plugin_loader.py", "plugin_router.py", "__init__.py"}
        if any(p in target for p in protected_files):
            return {"error": f"❌ ไม่อนุญาตให้แก้ไข {target} (protected file)"}

        existing = _read_snippet(target) if os.path.exists(
            os.path.join(PROJECT_ROOT, target)) else "(ไฟล์ใหม่)"

        # ── Call 2: เขียนโค้ด + retry สูงสุด 3 รอบ ───────────────────────
        messages = [
            {"role": "system", "content": (
                "เขียน Python function เท่านั้น\n"
                "ห้าม markdown ห้าม ``` ห้ามอธิบาย\n"
                "syntax ถูกต้อง: ทุก def ต้องมี : และ body >=1 บรรทัด"
            )},
            {"role": "user", "content": (
                f"เขียนฟังก์ชัน {func_name}: {description}\n\n"
                f"ไฟล์ปัจจุบัน:\n{existing}\n\n"
                "เขียนเฉพาะฟังก์ชันใหม่ ไม่ต้องเขียนทั้งไฟล์"
            )},
        ]

        last_err = ""
        for attempt in range(3):
            r2 = client.chat.completions.create(
                model=MODEL, max_tokens=600, messages=messages
            )
            new_code = r2.choices[0].message.content.strip()
            if "```" in new_code:
                new_code = "\n".join(
                    l for l in new_code.split("\n")
                    if not l.startswith("```")
                ).strip()

            ok, err = _validate(new_code)
            if ok:
                return {
                    "target_file":  target,
                    "action":       action,
                    "new_code":     new_code,
                    "insert_after": None,
                    "description":  description,
                    "error":        None,
                }

            last_err = err
            messages += [
                {"role": "assistant", "content": new_code},
                {"role": "user", "content": (
                    f"syntax ผิด: {err}\n"
                    "แก้ให้ถูกต้อง ตอบเฉพาะโค้ดเท่านั้น"
                )},
            ]

        return {"error": f"สร้างโค้ด syntax ผิดทุกรอบ ({3} tries): {last_err}"}

    except Exception as e:
        return {"error": str(e)}