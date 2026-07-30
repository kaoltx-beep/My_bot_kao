"""
dev_patcher.py — backup + apply patch + syntax check + rollback + git commit
Cross-platform: Windows, Termux/Android, Linux/macOS.
"""
import os
import shutil
import subprocess
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR = os.path.join(PROJECT_ROOT, "backups")


def _python_executable():
    """Use the same Python interpreter that runs Jarvis on every platform."""
    return sys.executable or "python"


def _backup(rel_path):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    src = os.path.join(PROJECT_ROOT, rel_path)
    if not os.path.exists(src):
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = rel_path.replace("/", "_").replace("\\", "_")
    dest = os.path.join(BACKUP_DIR, f"{safe_name}.{ts}.bak")
    shutil.copy2(src, dest)
    return dest


def _check_syntax(rel_path):
    if not rel_path.endswith(".py"):
        return True, "ไม่ใช่ .py ข้าม syntax check"

    full = os.path.join(PROJECT_ROOT, rel_path)
    try:
        r = subprocess.run(
            [_python_executable(), "-m", "py_compile", full],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
    except Exception as e:
        return False, f"❌ syntax check เรียก Python ไม่ได้: {e}"

    if r.returncode == 0:
        return True, "✅ syntax OK"
    return False, f"❌ syntax error:\n{r.stderr.strip()}"


def _git_commit(rel_path, description):
    """Stage only the changed target and create a local commit."""
    target = rel_path.replace("\\", "/")
    message = (description or f"Update {target}").strip()[:120]
    if not message:
        message = f"Update {target}"
    if not message.lower().startswith("jarvis"):
        message = f"Jarvis: {message}"

    try:
        add = subprocess.run(
            ["git", "add", "--", target],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if add.returncode != 0:
            return False, f"❌ git add ล้มเหลว: {(add.stderr or add.stdout).strip()[-500:]}"

        commit = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (commit.stdout or commit.stderr).strip()
        if commit.returncode != 0:
            return False, f"❌ git commit ล้มเหลว: {output[-700:]}"
        return True, f"✅ git commit สำเร็จ: {output[-500:]}"
    except FileNotFoundError:
        return False, "❌ ไม่พบคำสั่ง git บนเครื่องนี้"
    except Exception as e:
        return False, f"❌ git commit error: {e}"


def _rollback(rel_path, backup_path):
    if not backup_path or not os.path.exists(backup_path):
        return "ไม่มี backup"
    shutil.copy2(backup_path, os.path.join(PROJECT_ROOT, rel_path))
    return f"↩️ rollback {rel_path} สำเร็จ"


def apply_plan(plan):
    if plan.get("error"):
        return f"❌ Agent error: {plan['error']}"

    target = plan.get("target_file", "")
    action = plan.get("action", "")
    new_code = plan.get("new_code", "")
    insert_after = plan.get("insert_after")
    description = plan.get("description", "")

    if not target or not new_code:
        return "❌ plan ไม่ครบ: ขาด target_file หรือ new_code"

    backup_path = _backup(target)
    backup_note = (
        f"📦 backup: {os.path.basename(backup_path)}"
        if backup_path else "📦 ไฟล์ใหม่ (ไม่มี backup)"
    )

    full = os.path.join(PROJECT_ROOT, target)
    try:
        if action == "create_file" or not os.path.exists(full):
            parent = os.path.dirname(full)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(new_code)
            apply_note = f"สร้างไฟล์ใหม่: {target}"

        elif insert_after:
            with open(full, encoding="utf-8") as f:
                content = f.read()
            if insert_after in content:
                idx = content.find(insert_after) + len(insert_after)
                content = content[:idx] + "\n\n" + new_code + "\n" + content[idx:]
                apply_note = f"แทรกหลัง '{insert_after}'"
            else:
                content = content.rstrip() + "\n\n" + new_code + "\n"
                apply_note = f"ต่อท้าย {target} (insert_after ไม่พบ)"
            with open(full, "w", encoding="utf-8") as f:
                f.write(content)

        else:
            with open(full, "a", encoding="utf-8") as f:
                f.write("\n\n" + new_code + "\n")
            apply_note = f"ต่อท้าย {target}"

    except Exception as e:
        return f"❌ apply ล้มเหลว: {e}\n{backup_note}"

    passed, syntax_note = _check_syntax(target)
    if not passed:
        rb = _rollback(target, backup_path)
        return (
            "❌ Patch ล้มเหลว\n"
            f"{syntax_note}\n"
            f"{rb}\n"
            f"{backup_note}"
        )

    git_ok, git_note = _git_commit(target, description)

    return (
        "✅ Patch สำเร็จ!\n"
        f"📝 {description}\n"
        f"🔧 {apply_note}\n"
        f"{syntax_note}\n"
        f"{git_note}\n"
        f"{backup_note}"
    )


def replace(file_path, target, new_code, insert_after=None):
    backup_path = _backup(file_path)
    backup_note = (
        f"📦 backup: {os.path.basename(backup_path)}"
        if backup_path else "📦 ไฟล์ใหม่ (ไม่มี backup)"
    )

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        if insert_after:
            idx = content.find(insert_after) + len(insert_after)
            content = content[:idx] + "\n\n" + new_code + "\n" + content[idx:]
            apply_note = f"แทรกหลัง '{insert_after}'"
        else:
            content = content.rstrip() + "\n\n" + new_code + "\n"
            apply_note = f"ต่อท้าย {file_path}"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        return f"❌ apply ล้มเหลว: {e}\n{backup_note}"

    passed, syntax_note = _check_syntax(file_path)
    if not passed:
        return f"{apply_note}\n{syntax_note}\n" + _rollback(file_path, backup_path)

    git_ok, git_note = _git_commit(file_path, target or f"Update {file_path}")
    return f"{apply_note}\n{syntax_note}\n{git_note}\n{backup_note}"
