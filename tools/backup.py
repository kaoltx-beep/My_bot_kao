from pathlib import Path
from shutil import copy2
from datetime import datetime

backup_dir = Path("backups")
backup_dir.mkdir(exist_ok=True)

files = [
    "run.py",
    "device_actions.py",
    "memory_manager.py",
    "plugin_router.py",
]

now = datetime.now().strftime("%Y%m%d_%H%M%S")

for f in files:
    p = Path(f)
    if p.exists():
        dst = backup_dir / f"{p.stem}_{now}{p.suffix}"
        copy2(p, dst)
        print(f"✔ Backup: {dst}")

print("เสร็จเรียบร้อย")
