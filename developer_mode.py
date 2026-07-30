"""Safe Developer Mode workflow for Jarvis."""
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
DEV_MODEL = os.getenv("GROQ_DEV_MODEL", "openai/gpt-oss-20b")
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
    if rel in PROTECTED or any(rel == p or rel.startswith(p + "/") for p in PROTECTED if p == ".git"):
        raise ValueError("ไฟล์นี้ถูกป้องกัน ไม่อนุญาตให้ Developer Mode แก้")
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(f"ไม่รองรับไฟล์ประเภท {path.suffix}")
    return path


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


def _apply_operations(original: str, operations: list[dict[str, Any]]) -> str:
    updated = original
    for index, op in enumerate(operations, 1):
        old = str(op.get("old_text", ""))
        new = str(op.get("new_text", ""))
        if not old:
            raise ValueError(f"patch operation {index}: old_text ว่าง")
        count = updated.count(old)
        if count != 1:
            raise ValueError(f"patch operation {index}: old_text ต้องพบ 1 ครั้ง แต่พบ {count} ครั้ง")
        updated = updated.replace(old, new, 1)
    return updated


def _request_patch(groq_client, prompt: str) -> dict[str, Any]:
    """Use a minimal strict schema and low reasoning effort for patch generation."""
    schema = {"type": "object", "properties": {"old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["old_text", "new_text"], "additionalProperties": False}
    res = groq_client.chat.completions.create(
        model=DEV_MODEL,
        response_format={"type": "json_schema", "json_schema": {"name": "single_patch", "strict": True, "schema": schema}},
        messages=[{"role": "user", "content": prompt + "\nReturn exactly one JSON object with old_text and new_text."}],
        reasoning_effort="low",
        temperature=0.0,
        max_tokens=1200,
    )
    return json.loads(res.choices[0].message.content)


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
    prompt = f"""คุณเป็น Senior Python Developer ของ Jarvis.\nแก้ไฟล์ตามคำสั่งด้วยการแทนที่ข้อความเดิมเพียง 1 จุด\nต้องส่ง old_text เป็นข้อความที่มีอยู่จริงในไฟล์ และ new_text เป็นข้อความใหม่\nห้ามส่งไฟล์ทั้งไฟล์\n\nไฟล์: {filename}\nคำสั่ง: {text}\n\nเนื้อหาเดิม:\n---\n{original}\n---"""
    try:
        data = _request_patch(groq_client, prompt)
        old_text = data.get("old_text", "")
        new_text = data.get("new_text", "")
        new_content = _apply_operations(original, [{"old_text": old_text, "new_text": new_text}])
    except Exception as exc:
        return {"ok": False, "error": f"สร้าง patch ไม่สำเร็จ: {exc}"}
    if new_content == original:
        return {"ok": False, "error": "AI ไม่ได้สร้างการเปลี่ยนแปลงใหม่"}
    if path.suffix == ".py":
        try:
            ast.parse(new_content)
        except SyntaxError as exc:
            return {"ok": False, "error": f"patch ที่ AI สร้าง syntax ไม่ถูกต้อง: line {exc.lineno}: {exc.msg}"}
    proposal_id = uuid.uuid4().hex[:10]
    diff = "".join(difflib.unified_diff(original.splitlines(True), new_content.splitlines(True), fromfile=f"a/{filename}", tofile=f"b/{filename}"))
    session = {"id": proposal_id, "status": "pending", "created_at": datetime.now(timezone.utc).isoformat(), "file": filename, "summary": f"แก้ไข {filename} ตามคำสั่ง", "original": original, "new_content": new_content, "diff": diff, "operations": [{"old_text": old_text, "new_text": new_text}], "model": DEV_MODEL}
    _save_session(session)
    return {"ok": True, "proposal_id": proposal_id, "file": filename, "summary": session["summary"], "diff": diff}


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
            proc = subprocess.run([os.fspath(os.sys.executable), "-m", "py_compile", str(path)], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30)
            if proc.returncode != 0:
                shutil.copy2(backup, path)
                backup.unlink(missing_ok=True)
                session["status"] = "rolled_back"
                session["test"] = proc.stderr[-1500:] or proc.stdout[-1500:]
                _save_session(session)
                return {"ok": False, "status": "rolled_back", "error": "ทดสอบ syntax ไม่ผ่าน จึง rollback แล้ว", "test": session["test"]}
        if subprocess.run(["git", "status", "--short", "--", session["file"]], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30).returncode != 0:
            raise RuntimeError("git status failed")
        add = subprocess.run(["git", "add", "--", session["file"]], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30)
        if add.returncode != 0:
            raise RuntimeError(add.stderr.strip() or "git add failed")
        commit = subprocess.run(["git", "commit", "-m", f"Jarvis Developer Mode: update {session['file']}"], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30)
        if commit.returncode != 0:
            session["status"] = "tested_uncommitted"
            session["commit_error"] = commit.stderr.strip() or commit.stdout.strip()
            _save_session(session)
            return {"ok": False, "status": "tested_uncommitted", "error": "แก้ไขและทดสอบผ่านแล้ว แต่ commit ไม่สำเร็จ", "details": session["commit_error"]}
        backup.unlink(missing_ok=True)
        session["status"] = "committed"
        session["commit"] = commit.stdout.strip() or "committed"
        _save_session(session)
        return {"ok": True, "status": "committed", "file": session["file"], "message": "แก้ไข → ทดสอบ → commit สำเร็จ", "details": session["commit"]}
    except Exception as exc:
        try:
            if backup.exists():
                shutil.copy2(backup, path)
                backup.unlink(missing_ok=True)
        finally:
            session["status"] = "rolled_back"
            session["error"] = str(exc)
            _save_session(session)
        return {"ok": False, "status": "rolled_back", "error": f"เกิดข้อผิดพลาดและ rollback แล้ว: {exc}"}


def reject(proposal_id: str) -> dict[str, Any]:
    session = _load_session()
    if not session or session.get("id") != proposal_id:
        return {"ok": False, "error": "ไม่พบ proposal นี้"}
    session["status"] = "rejected"
    _save_session(session)
    return {"ok": True, "status": "rejected", "message": "ยกเลิก patch แล้ว"}


def rollback(proposal_id: str) -> dict[str, Any]:
    """Explicitly restore the backup from an applied/tested-uncommitted proposal."""
    session = _load_session()
    if not session or session.get("id") != proposal_id:
        return {"ok": False, "error": "ไม่พบ proposal นี้"}
    if session.get("status") not in {"applied", "tested_uncommitted", "committed"}:
        return {"ok": False, "error": f"ไม่สามารถ rollback จากสถานะ {session.get('status')}"}
    backup_name = session.get("backup")
    if not backup_name:
        return {"ok": False, "error": "ไม่พบ backup สำหรับ proposal นี้"}
    backup = PROJECT_ROOT / backup_name
    if not backup.exists():
        return {"ok": False, "error": "ไม่พบไฟล์ backup แล้ว"}
    path = _safe_path(session["file"])
    try:
        shutil.copy2(backup, path)
        backup.unlink(missing_ok=True)
        session["status"] = "rolled_back"
        _save_session(session)
        return {"ok": True, "status": "rolled_back", "file": session["file"], "message": "rollback เสร็จแล้ว"}
    except Exception as exc:
        return {"ok": False, "error": f"rollback ไม่สำเร็จ: {exc}"}


def self_test_rollback() -> dict[str, Any]:
    target = PROJECT_ROOT / "tests" / "_developer_auto_rollback_test.py"
    backup = target.with_name(target.name + ".backup_test")
    original = "print('rollback-original')\n"
    broken = "def broken(:\n"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(original, encoding="utf-8")
        shutil.copy2(target, backup)
        target.write_text(broken, encoding="utf-8")
        proc = subprocess.run([os.fspath(os.sys.executable), "-m", "py_compile", str(target)], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30)
        if proc.returncode == 0:
            return {"ok": False, "status": "failed", "error": "ทดสอบ rollback ไม่ล้มเหลวตามที่คาด"}
        shutil.copy2(backup, target)
        if target.read_text(encoding="utf-8") != original:
            return {"ok": False, "status": "failed", "error": "rollback คืนเนื้อหาไม่ตรงของเดิม"}
        return {"ok": True, "status": "rolled_back", "message": "Apply → Test fail → Rollback ผ่าน"}
    except Exception as exc:
        return {"ok": False, "status": "failed", "error": f"rollback self-test ล้มเหลว: {exc}"}
    finally:
        target.unlink(missing_ok=True)
        backup.unlink(missing_ok=True)
        pycache = target.parent / "__pycache__"
        if pycache.exists():
            for item in pycache.glob(target.stem + ".*.pyc"):
                item.unlink(missing_ok=True)


def system_status() -> dict[str, Any]:
    session = _load_session()
    try:
        git = subprocess.run(["git", "branch", "--show-current"], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=10)
        branch = git.stdout.strip() or "unknown"
    except Exception:
        branch = "unknown"
    return {"ok": True, "status": "online", "project": PROJECT_ROOT.name, "branch": branch, "developer_mode": "ready", "model": DEV_MODEL, "max_file_chars": MAX_FILE_CHARS, "pending_proposal": session.get("id") if session.get("status") == "pending" else None, "protected_files": sorted(PROTECTED)}


def handle(text: str, groq_client=None) -> dict[str, Any]:
    normalized = text.lower()
    if any(k in normalized for k in ("สร้าง patch", "ช่วยแก้โค้ด", "แก้โค้ด", "แก้ไฟล์")):
        return prepare_patch(text, groq_client)
    filename = _extract_filename(text)
    if filename:
        return analyze_file(filename)
    return {"ok": False, "error": "Developer Mode: ระบุไฟล์หรือใช้คำสั่ง 'สร้าง patch run.py ...'"}
