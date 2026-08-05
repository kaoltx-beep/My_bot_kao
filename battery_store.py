"""Battery status store with safe fallbacks for non-Android environments."""
from __future__ import annotations

import subprocess
import json
from typing import Optional

# Public state
level: int = -1
status: str = "unknown"
latest_battery: str = "ไม่ทราบ"


def _compose_latest() -> None:
    global latest_battery
    try:
        if level >= 0:
            latest_battery = f"{level}% ({status})"
        else:
            latest_battery = "ไม่สามารถดึงข้อมูลแบตเตอรี่ได้"
    except Exception:
        latest_battery = "ไม่สามารถดึงข้อมูลแบตเตอรี่ได้"


def update() -> None:
    """Try multiple platform-specific methods, but never raise to caller.

    Order:
    1. termux-battery-status (Termux Android)
    2. dumpsys battery (Android)
    3. fallback to unknown
    """
    global level, status

    # Default when not available
    level = -1
    status = "unknown"

    # Method 1: termux-battery-status
    try:
        raw = subprocess.check_output(["termux-battery-status"], text=True)
        data = json.loads(raw)
        level = int(data.get("percentage", 0))
        raw_status = str(data.get("status", "")).upper()
        status = "กำลังชาร์จ ⚡" if raw_status == "CHARGING" else "ไม่ได้ชาร์จ 🔋"
        if level <= 20:
            status += " ⚠️ (แบตเตอรี่ต่ำ)"
        _compose_latest()
        return
    except Exception:
        # Not running on Termux or termux not available
        pass

    # Method 2: dumpsys battery (Android)
    try:
        raw = subprocess.check_output(["sh", "-c", "dumpsys battery"], text=True)
        for line in raw.splitlines():
            if "level:" in line:
                try:
                    level = int(line.split(":")[1].strip())
                except Exception:
                    level = -1
            if "status:" in line:
                # status line on dumpsys often contains numeric codes
                status = "กำลังชาร์จ ⚡" if "2" in line else "ไม่ได้ชาร์จ 🔋"
        _compose_latest()
        return
    except Exception:
        # Not available on server environments
        level = -1
        status = "ไม่สามารถดึงข้อมูลระบบได้"

    _compose_latest()
