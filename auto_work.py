# auto_work.py
# ─────────────────────────────────────────────────────────────────────────────
# Detects fiber installation work messages and auto-saves them to the job DB.
# Called from run.py worker() before normal intent routing.
# ─────────────────────────────────────────────────────────────────────────────

import re

# Keywords (Thai + English) that indicate a fiber installation job
WORK_KEYWORDS = [
    "ติดตั้ง", "ไฟเบอร์", "fiber", "fibre",
    "3bb", "true", "ais", "nt fiber",
]

# Matches known ISP provider names
_PROVIDER_PATTERN = re.compile(
    r"\b(3bb|true|ais|nt)\b",
    re.IGNORECASE,
)

# Matches "ลูกค้า <name>" pattern
_CUSTOMER_PATTERN = re.compile(
    r"ลูกค้า\s*([ก-๙a-zA-Z\s]+?)(?:\s+(?:ที่|อยู่|ผู้ให้บริการ|3bb|true|ais|nt)|$)",
    re.IGNORECASE,
)


def save_auto_work(text: str):
    """
    Check if the message describes a work installation job and auto-save it.

    Returns:
        True        — job detected and saved successfully
        "duplicate" — job was already recorded today
        None        — message is not a work job; continue normal routing
    """
    text_lower = text.lower()

    # Quick filter: must contain at least one work keyword
    if not any(kw in text_lower for kw in WORK_KEYWORDS):
        return None

    # Don't intercept query commands like "ดูงานทั้งหมด"
    if any(q in text_lower for q in ["ดูงาน", "รายการงาน", "งานทั้งหมด", "สถานะงาน"]):
        return None

    try:
        from job_database import is_duplicate, save_job
    except ImportError:
        return None

    # Extract provider
    provider_match = _PROVIDER_PATTERN.search(text)
    provider = provider_match.group(0).upper() if provider_match else "ไม่ระบุ"

    # Extract customer name (best-effort)
    customer_match = _CUSTOMER_PATTERN.search(text)
    customer = customer_match.group(1).strip() if customer_match else "ไม่ระบุ"

    # Use full message as address/description (full context is most useful)
    address = text.strip()

    try:
        if is_duplicate(customer, provider, address):
            return "duplicate"
        save_job(customer, provider, address, status="รับงาน", note="auto-detected")
        return True
    except Exception:
        # If DB call fails, fall through to normal routing rather than crashing
        return None
