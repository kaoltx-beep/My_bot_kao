"""Safe Developer Mode patching: backup, apply, syntax check, rollback."""

import os
import shutil
import subprocess
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(PROJECT_ROOT, "backups")


def _safe_path(rel_path):
    rel_path = str(rel_path).replace("\\", "/").lstrip("/")
    full = os.path.realpath(os.path.join(PROJECT_ROOT, rel_path))
    root = os.path.realpath(PROJECT_ROOT)
    if full != root and not full.startswith(root + os.sep):
        raise ValueError("target path escapes project root")
    return full, rel_path


def _backup(rel_path):
    full, rel = _safe_path(rel_path)
    if not os.path.exists(full):
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = rel.replace("/", "_")
    dest = os.path.join(BACKUP_DIR, f"{safe_name}.{ts}.bak")
    shutil.copy2(full, dest)
    return dest


def _check_syntax(rel_path):
    full, rel = _safe_path(rel_path)
    if not rel.endswith(".py"):
        return True, "syntax check skipped (not Python)"
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", full],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True, "✅ syntax OK"
    return False, f"❌ syntax error:\n{result.stderr.strip()}"


def _rollback(rel_path, backup_path, created_new=False):
    full, _ = _safe_path(rel_path)
    if backup_path and os.path.exists(backup_path):
        shutil.copy2(backup_path, full)
        return f"↩️ rollback {rel_path} สำเร็จ"
    if created_new and os.path.exists(full):
        os.remove(full)
        return f"↩️ ลบไฟล์ใหม่ {rel_path} หลัง patch ล้มเหลว"
    return "ไม่พบ backup สำหรับ rollback"


def apply_plan(plan):
    """Apply an approved plan. The caller must explicitly approve first."""
    if not isinstance(plan, dict):
        return "❌ patch plan ไม่ถูกต้อง"
    if plan.get("error"):
        return f"❌ Agent error: {plan['error']}"

    target = str(plan.get("target_file", "")).strip()
    action = str(plan.get("action", "add_function")).strip()
    new_code = str(plan.get("new_code", ""))
    insert_after = plan.get("insert_after")
    description = str(plan.get("description", "")).strip()

    if not target or not new_code:
        return "❌ plan ไม่ครบ: ขาด target_file หรือ new_code"

    try:
        full, rel = _safe_path(target)
    except Exception as exc:
        return f"❌ target ไม่ปลอดภัย: {exc}"

    protected = {
        "run.py", "config.py", ".env", "__init__.py",
        "developer_mode_router.py", "dev_patcher.py", "dev_agent.py",
        "dev_session.py", "plugin_loader.py", "plugin_router.py",
    }
    if rel in protected or os.path.basename(rel) in protected:
        return f"❌ ไม่อนุญาตให้แก้ไฟล์ protected: {rel}"

    existed = os.path.exists(full)
    backup_path = _backup(rel)
    backup_note = (
        f"📦 backup: {os.path.basename(backup_path)}"
        if backup_path else "📦 ไฟล์ใหม่ ไม่มี backup"
    )

    try:
        if action == "create_file" or not existed:
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as handle:
                handle.write(new_code.rstrip() + "\n")
            apply_note = f"สร้างไฟล์ใหม่: {rel}"
            created_new = not existed
        else:
            with open(full, encoding="utf-8") as handle:
                content = handle.read()

            if insert_after and insert_after in content:
                idx = content.find(insert_after) + len(insert_after)
                content = content[:idx] + "\n\n" + new_code.rstrip() + "\n" + content[idx:]
                apply_note = f"แทรกหลัง '{insert_after}'"
            else:
                content = content.rstrip() + "\n\n" + new_code.rstrip() + "\n"
                apply_note = f"ต่อท้าย {rel}"

            with open(full, "w", encoding="utf-8") as handle:
                handle.write(content)
            created_new = False
    except Exception as exc:
        return f"❌ apply ล้มเหลว: {exc}\n{backup_note}"

    passed, syntax_note = _check_syntax(rel)
    if not passed:
        rollback_note = _rollback(rel, backup_path, created_new=created_new)
        return f"❌ Patch ล้มเหลว\n{syntax_note}\n{rollback_note}\n{backup_note}"

    return (
        "✅ Patch สำเร็จ!\n"
        f"📝 {description or 'ไม่มีคำอธิบาย'}\n"
        f"🔧 {apply_note}\n"
        f"{syntax_note}\n"
        f"{backup_note}"
    )
