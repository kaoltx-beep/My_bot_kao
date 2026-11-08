from __future__ import annotations

import base64
import hashlib
import hmac
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
_GRANT_SECRET = secrets.token_bytes(32)
_USED_GRANTS: set[str] = set()


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


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _issue_grant(item: dict[str, Any]) -> str:
    payload = {
        "grant_id": secrets.token_urlsafe(18),
        "tool": item["tool"],
        "params": item["params"],
        "chat_id": item["chat_id"],
        "user_id": item["user_id"],
        "expires_at": item["expires_at"],
    }
    encoded = base64.urlsafe_b64encode(_canonical(payload)).decode("ascii").rstrip("=")
    signature = hmac.new(_GRANT_SECRET, encoded.encode("ascii"), hashlib.sha256).hexdigest()
    return encoded + "." + signature


def validate_and_consume_grant(
    grant: str | None,
    *,
    tool_name: str,
    params: dict[str, Any],
    now: float | None = None,
) -> bool:
    """Validate an opaque, one-use grant created only by consume()."""
    if not isinstance(grant, str) or "." not in grant:
        return False
    encoded, supplied_signature = grant.rsplit(".", 1)
    expected = hmac.new(_GRANT_SECRET, encoded.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied_signature, expected):
        return False
    try:
        padded = encoded + "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (ValueError, UnicodeError, json.JSONDecodeError):
        return False
    current_time = time.time() if now is None else float(now)
    if payload.get("tool") != tool_name or _canonical(payload.get("params")) != _canonical(params):
        return False
    try:
        if current_time >= float(payload["expires_at"]):
            return False
    except (KeyError, TypeError, ValueError):
        return False
    grant_id = payload.get("grant_id")
    if not isinstance(grant_id, str) or not grant_id:
        return False
    with _LOCK:
        if grant_id in _USED_GRANTS:
            return False
        _USED_GRANTS.add(grant_id)
    return True


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
            item["status"] = "expired"
            _save(data)
            return None
        if current_time >= expires_at:
            item["status"] = "expired"
            _save(data)
            return None

        item["status"] = status
        item["consumed_at"] = current_time
        result = dict(item)
        if status == "approved":
            result["approval_grant"] = _issue_grant(item)
        _save(data)
        return result
