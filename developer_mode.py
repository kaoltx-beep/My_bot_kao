"""Safe Developer Mode workflow for Jarvis.

Flow: analyze -> propose -> approve -> backup/apply -> syntax test -> commit.
A failed test automatically restores the backup. Only project files are allowed.
"""
from __future__ import annotations

import ast
import difflib
import json
import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
SESSION_FILE = PROJECT_ROOT / "data" / "developer_session.json"
MAX_FILE_CHARS = 20000
PROTECTED = {".env", ".git", "config.py", "data/developer_session.json"}
ALLOWED_EXTENSIONS = {".py", ".txt", ".md", ".json", ".sh", ".cfg", ".ini"}


def _load_session() -> dict[str, Any]:
    try:
        if SESSION_FILE.exists():
            return json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_session(data: dict[str, Any]) -> None:
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = SESSION_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(SESSION_FILE)


def _safe_path(filename: str) -> Path:
    raw = filename.strip().replace("\\", "/")
    path = (PROJECT_ROOT / raw).resolve()
    root = PROJECT_ROOT.resolve()
    if path != root and root not in path.parents:
        raise ValueError("ไฟล์อยู่นอก project ไม่อนุญาต")
    rel = path.relative_to(root).as_posix()
    if rel in PROTECTED or any(rel == p or rel.startswith(p + "/") for p in PROTECTED if p in {".git"}):
        raise ValueError("ไฟล์นี้ถูกป้องกัน ไม่อนุญาตให้ Developer Mode แก้")
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(f"ไม่รองรับไฟล์ประเภท {path.suffix}")
    return path


def _read(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text if len(text) <= MAX_FILE_CHARS else text[:MAX_FILE_CHARS] + "\n# ... TRUNCATED ..."


def analyze_file(filename: str) -> dict[str, Any]:
    path = _safe_path(filename)
    if not path.exists():
        return {"ok": False, "error": f"ไม่พบไฟล์ {filename}"}
    content = path.read_text(encoding="utf-8")
    result: dict[str, Any] = {"ok": True, "file": str(path.relative_to(PROJECT_ROOT)), "lines": len(content.splitlines()), "errors": []}
    if path.suffix == ".py":
        try:
            ast.parse(content)
        except SyntaxError as exc:
            result["ok"] = False
            result["errors"].append(f"SyntaxError line {exc.lineno}: {exc.msg}")
    return result


def _extract_filename(text: str) -> str | None:
    match = re.search(r"([\w./-]+\.(?:py|txt|md|json|sh|cfg|ini))", text, re.I)
    return match.group(1) if match else None


def _clean_model_code(value: str) -> str:
    value = value.strip()
    if value.startswith("```"):
        value = re.sub(r"^```[a-zA-Z0-9_+-]*\n", "", value)
        if value.endswith("```"):
            value = value[:-3]
    return value.strip() + "\n"


def prepare_patch(text: str, groq_client=None) -> dict[str, Any]:
    filename = _extract_filename(text)
    if not filename:
        return {"ok": False, "error": "ต้องระบุชื่อไฟล์ เช่น run.py"}
    if groq_client is None:
        return {"ok": False, "error": "ยังไม่ได้เชื่อมต่อ AI สำหรับสร้าง patch"}

    path = _safe_path(filename)
    if not path.exists():
        return {"ok": False, "error": f"ไม่พบไฟล์ {filename}"}
    original = path.read_text(encoding="utf-8")
    if len(original) > MAX_FILE_CHARS:
        return {"ok": False, "error": f"ไฟล์ใหญ่เกิน {MAX_FILE_CHARS} ตัวอักษรสำหรับ patch อัตโนมัติ"}

    prompt = f"""คุณเป็น Senior Python Developer ของ Jarvis.
แก้ไฟล์ตามคำสั่งด้านล่าง และส่ง JSON เท่านั้นในรูปแบบ:
{{\"new_content\":\"เนื้อหาไฟล์ใหม่ทั้งหมด\",\"summary\":\"สรุปการแก้ 1-3 ข้อ\"}}
ห้ามแก้ไฟล์อื่น ห้ามตัดโค้ดส่วนที่ไม่เกี่ยวข้อง และต้องส่งเนื้อหาไฟล์ใหม่ครบทั้งไฟล์

ไฟล์: {filename}
คำสั่ง: {text}

เนื้อหาเดิม:
---
{original}
---"""
    try:
        res = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=5000,
        )
        data = json.loads(res.choices[0].message.content)
        new_content = _clean_model_code(str(data.get("new_content", "")))
        summary = str(data.get("summary", "แก้ไขตามคำสั่ง"))
    except Exception as exc:
        return {"ok": False, "error": f"สร้าง patch ไม่สำเร็จ: {exc}"}

    if not new_content or new_content == original:
        return {"ok": False, "error": "AI ไม่ได้สร้างการเปลี่ยนแปลงใหม่"}
    if path.suffix == ".py":
        try:
            ast.parse(new_content)
        except SyntaxError as exc:
            return {"ok": False, "error": f"patch ที่ AI สร้าง syntax ไม่ถูกต้อง: line {exc.lineno}: {exc.msg}"}

    proposal_id = uuid.uuid4().hex[:10]
    diff = "".join(difflib.unified_diff(
        original.splitlines(True), new_content.splitlines(True),
        fromfile=f"a/{filename}", tofile=f"b/{filename}",
    ))
    session = {
        "id": proposal_id,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "file": filename,
        "summary": summary,
        "original": original,
        "new_content": new_content,
        "diff": diff,
    }
    _save_session(session)
    return {"ok": True, "proposal_id": proposal_id, "file": filename, "summary": summary, "diff": diff}


def approve(proposal_id: str) -> dict[str, Any]:
    session = _load_session()
    if not session or session.get("id") != proposal_id:
        return {"ok": False, "error": "ไม่พบ proposal นี้"}
    if session.get("status") != "pending":
        return {"ok": False, "error": f"proposal อยู่ในสถานะ {session.get('status')}"}

    path = _safe_path(session["file"])
    backup = path.with_name(path.name + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    try:
        shutil.copy2(path, backup)
        path.write_text(session["new_content"], encoding="utf-8")
        session["backup"] = str(backup.relative_to(PROJECT_ROOT))
        session["status"] = "applied"
        _save_session(session)

        if path.suffix == ".py":
            proc = subprocess.run(
                [os.fspath(os.sys.executable), "-m", "py_compile", str(path)],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode != 0:
                shutil.copy2(backup, path)
                backup.unlink(missing_ok=True)
                session["status"] = "rolled_back"
                session["test"] = proc.stderr[-1500:] or proc.stdout[-1500:]
                _save_session(session)
                return {"ok": False, "error": "ทดสอบ syntax ไม่ผ่าน จึง rollback แล้ว", "test": session["test"]}

        proc = subprocess.run(
            ["git", "status", "--short", "--", session["file"]],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "git status failed")

        add = subprocess.run(["git", "add", "--", session["file"]], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30)
        if add.returncode != 0:
            raise RuntimeError(add.stderr.strip() or "git add failed")
        commit = subprocess.run(
            ["git", "commit", "-m", f"Jarvis Developer Mode: update {session['file']}"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if commit.returncode != 0:
            session["status"] = "tested_uncommitted"
            session["commit_error"] = commit.stderr.strip() or commit.stdout.strip()
            _save_session(session)
            return {"ok": False, "error": "แก้ไขและทดสอบผ่านแล้ว แต่ commit ไม่สำเร็จ", "details": session["commit_error"]}

        backup.unlink(missing_ok=True)
        session["status"] = "committed"
        session["commit"] = commit.stdout.strip() or "committed"
        _save_session(session)
        return {"ok": True, "status": "committed", "message": "แก้ไข → ทดสอบ → commit สำเร็จ", "details": session["commit"]}
    except Exception as exc:
        try:
            if backup.exists():
                shutil.copy2(backup, path)
                backup.unlink(missing_ok=True)
        finally:
            session["status"] = "rolled_back"
            session["error"] = str(exc)
            _save_session(session)
        return {"ok": False, "error": f"เกิดข้อผิดพลาดและ rollback แล้ว: {exc}"}


def reject(proposal_id: str) -> dict[str, Any]:
    session = _load_session()
    if not session or session.get("id") != proposal_id:
        return {"ok": False, "error": "ไม่พบ proposal นี้"}
    session["status"] = "rejected"
    _save_session(session)
    return {"ok": True, "message": "ยกเลิก patch แล้ว"}


def handle(text: str, groq_client=None) -> dict[str, Any]:
    normalized = text.lower()
    if any(k in normalized for k in ("สร้าง patch", "ช่วยแก้โค้ด", "แก้โค้ด", "แก้ไฟล์")):
        return prepare_patch(text, groq_client)
    filename = _extract_filename(text)
    if filename:
        return analyze_file(filename)
    return {"ok": False, "error": "Developer Mode: ระบุไฟล์หรือใช้คำสั่ง 'สร้าง patch run.py ...'"}
