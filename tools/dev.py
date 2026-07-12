import sys
import subprocess
from pathlib import Path
from shutil import copy2
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent

def backup():
    backup_dir = ROOT / "backups"
    backup_dir.mkdir(exist_ok=True)

    files = [
        "run.py",
        "device_actions.py",
        "memory_manager.py",
        "plugin_router.py",
    ]

    now = datetime.now().strftime("%Y%m%d_%H%M%S")

    for f in files:
        p = ROOT / f
        if p.exists():
            dst = backup_dir / f"{p.stem}_{now}{p.suffix}"
            copy2(p, dst)
            print(f"✔ Backup: {dst.name}")

    print("✅ Backup เสร็จ")

def health():
    print("=== Jarvis Health Check ===")

    files = [
        "run.py",
        "config.py",
        "memory_manager.py",
        "plugin_loader.py",
        "plugin_router.py",
    ]

    for f in files:
        print(("✔" if (ROOT / f).exists() else "✘"), f)

    print("\nตรวจสอบ Syntax ของ run.py")
    r = subprocess.run(
        ["python", "-m", "py_compile", "run.py"],
        cwd=ROOT
    )

    if r.returncode == 0:
        print("✅ run.py OK")
    else:
        print("❌ run.py มี Syntax Error")

cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

if cmd == "backup":
    backup()
elif cmd == "health":
    health()
else:
    print("คำสั่งที่ใช้ได้:")
    print("  python tools/dev.py backup")
    print("  python tools/dev.py health")
