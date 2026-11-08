from __future__ import annotations

import json
import secrets
import time
from pathlib import Path
from threading import Lock
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "data" / "tool_approvals.json"
_LOCK = Lock()
DEFAULT_TTL_SECONDS = 300
MAX_TTL_SECONDS = 900


def _load() -> dict[str, Any]:
    try:
        if STORE.exists():
            data = json.loads(STORE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _save(data: dict[str, Any]) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STORE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STORE)


def create(
    tool_name: str,
    params: dict[str, Any],
    chat_id: int,
    user_id: int,
    *,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    now: float | None = None,
) -> str:
    """Create a one-use approval bound to the requesting chat and user."""
    if not isinstance(tool_name, str) or not tool_name.strip():
        raise ValueError("tool_name is required")
    if not isinstance(params, dict):
        raise TypeError("params must be a dictionary")
    if int(chat_id) == 0 or int(user_id) <= 0:
        raise ValueError("valid chat_id and user_id are required")
    if not 1 <= int(ttl_seconds) <= MAX_TTL_SECONDS:
        raise ValueError(f"ttl_seconds must be between 1 and {MAX_TTL_SECONDS}")

    created_at = time.time() if now is None else float(now)
    approval_id = secrets.token_urlsafe(24)
    with _LOCK:
        data = _load()
        data[approval_id] = {
            "tool": tool_name.strip(),
            "params": params,
            "chat_id": int(chat_id),
            "user_id": int(user_id),
            "status": "pending",
            "created_at": created_at,
            "expires_at": created_at + int(ttl_seconds),
        }
        _save(data)
    return approval_id


def get(approval_id: str) -> dict[str, Any] | None:
    with _LOCK:
        item = _load().get(approval_id)
        return dict(item) if isinstance(item, dict) else None


def consume(
    approval_id: str,
    status: str,
    *,
    chat_id: int,
    user_id: int,
    now: float | None = None,
) -> dict[str, Any] | None:
    """Atomically consume a pending approval only for its owner, before expiry."""
    if status not in {"approved", "rejected"}:
        raise ValueError("status must be approved or rejected")
    if int(chat_id) == 0 or int(user_id) <= 0:
        return None

    current_time = time.time() if now is None else float(now)
    with _LOCK:
        data = _load()
        item = data.get(approval_id)
        if not isinstance(item, dict) or item.get("status") != "pending":
            return None
        if item.get("chat_id") != int(chat_id) or item.get("user_id") != int(user_id):
            return None
        try:
            expires_at = float(item["expires_at"])
        except (KeyError, TypeError, ValueError):
            # Legacy approval records without expiry are invalid and fail closed.
            item["status"] = "expired"
            _save(data)
            return None
        if current_time >= expires_at:
            item["status"] = "expired"
            _save(data)
            return None

        item["status"] = status
        item["consumed_at"] = current_time
        _save(data)
        return dict(item)
