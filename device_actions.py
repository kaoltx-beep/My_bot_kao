"""Device action helpers with safe fallbacks for server environments."""
from __future__ import annotations

import requests
import typing

import config
import battery_store


def check_battery() -> str:
    """Return a human-friendly battery status. Safe if running on a server (no Termux)."""
    try:
        battery_store.update()
    except Exception:
        # ensure we never raise from a status check
        pass

    # prefer a composed latest string if available
    latest = getattr(battery_store, "latest_battery", None)
    if latest:
        return f"🔋 {latest}"

    # fallback to legacy fields
    level = getattr(battery_store, "level", -1)
    status = getattr(battery_store, "status", "unknown")
    if isinstance(level, int) and level >= 0:
        return f"🔋 {level}% ({status})"
    return "🔋 ข้อมูลแบตเตอรี่ไม่พร้อมใช้งาน"


def open_youtube() -> str:
    """Trigger MacroDroid webhook if configured; otherwise return a friendly message."""
    try:
        url = getattr(config, "MACRODROID_WEBHOOK_URL", None)
        if not url:
            return "📺 ฟีเจอร์ MacroDroid ยังไม่ได้ตั้งค่า"

        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return "📺 ส่งคำสั่งเปิด YouTube ให้ MacroDroid แล้วครับ"
        return f"❌ MacroDroid ตอบกลับ {resp.status_code}"
    except Exception as exc:
        return f"❌ เปิด YouTube ไม่สำเร็จ: {exc}"


def execute_device_action(action_text: str) -> typing.Optional[str]:
    """Legacy helper to preserve compatibility with older code paths."""
    if not action_text:
        return None

    if "เช็คแบต" in action_text or "check_battery" in action_text:
        return check_battery()

    if "เปิดยูทูป" in action_text or "open_youtube" in action_text:
        return open_youtube()

    return None
