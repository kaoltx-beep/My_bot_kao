from __future__ import annotations

import json
import uuid
from pathlib import Path
from threading import Lock
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "data" / "tool_approvals.json"
_LOCK = Lock()


def _load() -> dict[str, Any]:
    try:
        if STORE.exists():
            return json.loads(STORE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save(data: dict[str, Any]) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STORE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STORE)


def create(tool_name: str, params: dict[str, Any], chat_id: int) -> str:
    approval_id = uuid.uuid4().hex[:10]
    with _LOCK:
        data = _load()
        data[approval_id] = {
            "tool": tool_name,
            "params": params,
            "chat_id": chat_id,
            "status": "pending",
        }
        _save(data)
    return approval_id


def get(approval_id: str) -> dict[str, Any] | None:
    with _LOCK:
        return _load().get(approval_id)


def consume(approval_id: str, status: str) -> dict[str, Any] | None:
    with _LOCK:
        data = _load()
        item = data.get(approval_id)
        if not item or item.get("status") != "pending":
            return None
        item["status"] = status
        _save(data)
        return item
