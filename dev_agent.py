"""Groq-backed Developer Mode agent for proposing safe code patches."""

import ast
import json
import os

from groq import Groq
from config import GROQ_API_KEY

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
READABLE_EXT = {".py", ".txt", ".md", ".json"}
PROTECTED = {
    "run.py",
    "config.py",
    ".env",
    "developer_mode_router.py",
    "dev_agent.py",
    "dev_patcher.py",
    "dev_session.py",
    "plugin_loader.py",
    "plugin_router.py",
}
MAX_LINES = 140
MAX_FILES = 6
MODEL = "llama-3.1-8b-instant"


def _validate(code):
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as exc:
        return False, str(exc)


def _list_files():
    result = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", ".git", "backups"}]
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext not in READABLE_EXT:
                continue
            rel = os.path.relpath(os.path.join(root, name), PROJECT_ROOT)
            if os.path.basename(rel) in PROTECTED:
                continue
            result.append(rel.replace("\\", "/"))
    return sorted(result)


def _read_snippet(rel_path):
    full = os.path.realpath(os.path.join(PROJECT_ROOT, rel_path))
    root = os.path.realpath(PROJECT_ROOT)
    if not (full == root or full.startswith(root + os.sep)):
        return "[อ่านไม่ได้: unsafe path]"
    try:
        with open(full, encoding="utf-8") as handle:
            lines = handle.readlines()
    except Exception as exc:
        return f"[อ่านไม่ได้: {exc}]"
    out = "".join(lines[:MAX_LINES])
    if len(lines) > MAX_LINES:
        out += f"\n...(ตัดที่ {MAX_LINES}/{len(lines)})"
    return out


def _pick_files(request, all_files):
    req = request.lower()
    priority, fallback = [], []
    for rel in all_files:
        tokens = rel.lower().replace("/", " ").replace("_", " ").replace(".", " ").split()
        if any(token and token in req for token in tokens):
            priority.append(rel)
        elif rel.endswith(".py"):
            fallback.append(rel)
    return (priority if priority else fallback[:4])[:MAX_FILES]


def _extract_json(text):
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return None
    return None


def analyze(user_request):
    """Return a patch proposal only. Never writes files."""
    try:
        client = Groq(api_key=GROQ_API_KEY)
        all_files = _list_files()
        relevant = _pick_files(user_request, all_files)
        context = "\n".join(f"### {rel}\n{_read_snippet(rel)}" for rel in relevant)

        plan_response = client.chat.completions.create(
            model=MODEL,
            max_tokens=220,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "ตอบ JSON บรรทัดเดียวเท่านั้น\n"
                        '{"target_file":"path","action":"add_function","function_name":"name",'
                        '"description":"text","insert_after":null}\n'
                        "เลือก target_file จากไฟล์ที่มีอยู่ใน list เท่านั้น\n"
                        "ห้ามเลือก run.py, config.py, .env, developer_mode_router.py, dev_agent.py, dev_patcher.py, dev_session.py, plugin_loader.py, plugin_router.py\n"
                        "ห้ามเสนอการลบไฟล์หรือการเปลี่ยน dependency\n"
                    ),
                },
                {
                    "role": "user",
                    "content": f"คำสั่ง: {user_request}\nไฟล์: {all_files}\n{context}",
                },
            ],
        )
        plan = _extract_json(plan_response.choices[0].message.content.strip())
        if not plan:
            return {"error": "AI ไม่ได้ตอบ plan JSON ที่ถูกต้อง"}

        target = str(plan.get("target_file", "")).replace("\\", "/")
        if not target or target not in all_files:
            return {"error": f"target_file ไม่ถูกต้อง: {target}"}
        if os.path.basename(target) in PROTECTED:
            return {"error": f"protected file: {target}"}

        existing = _read_snippet(target)
        function_name = str(plan.get("function_name", "new_function"))
        description = str(plan.get("description", user_request))
        insert_after = plan.get("insert_after")
        if insert_after is not None:
            insert_after = str(insert_after)

        messages = [
            {
                "role": "system",
                "content": (
                    "เขียน Python function ใหม่เพียงหนึ่งฟังก์ชัน\n"
                    "ห้าม markdown ห้าม ``` ห้ามคำอธิบาย\n"
                    "ต้อง parse ได้ด้วย ast.parse และห้ามมี import เพิ่ม\n"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"สร้างฟังก์ชัน {function_name}: {description}\n"
                    f"ไฟล์ปัจจุบัน:\n{existing}\n"
                    "ตอบเฉพาะฟังก์ชันใหม่"
                ),
            },
        ]

        last_error = ""
        for _ in range(3):
            response = client.chat.completions.create(
                model=MODEL,
                max_tokens=700,
                messages=messages,
            )
            new_code = response.choices[0].message.content.strip()
            if "```" in new_code:
                new_code = "\n".join(line for line in new_code.splitlines() if not line.strip().startswith("```"))
            ok, error = _validate(new_code)
            if ok:
                return {
                    "target_file": target,
                    "action": str(plan.get("action", "add_function")),
                    "new_code": new_code,
                    "insert_after": insert_after,
                    "description": description,
                }
            last_error = error or "unknown syntax error"
            messages.extend([
                {"role": "assistant", "content": new_code},
                {"role": "user", "content": f"syntax ผิด: {last_error}\nแก้ใหม่ ตอบเฉพาะโค้ด"},
            ])

        return {"error": f"สร้างโค้ดไม่ผ่าน syntax หลัง 3 ครั้ง: {last_error}"}
    except Exception as exc:
        return {"error": str(exc)}
