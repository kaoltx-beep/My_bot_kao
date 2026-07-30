from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "data" / "tool_tasks.json"
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


def create(task: str, max_steps: int = 5) -> dict[str, Any]:
    task_id = uuid.uuid4().hex[:10]
    item = {
        "id": task_id,
        "task": task,
        "status": "pending",
        "step": 0,
        "max_steps": max(1, min(int(max_steps), 10)),
        "steps": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with _LOCK:
        data = _load()
        data[task_id] = item
        _save(data)
    return item


def get(task_id: str) -> dict[str, Any] | None:
    with _LOCK:
        return _load().get(task_id)


def record_step(task_id: str, step: dict[str, Any]) -> dict[str, Any] | None:
    with _LOCK:
        data = _load()
        item = data.get(task_id)
        if item is None:
            return None
        item["step"] += 1
        item["steps"].append(step)
        _save(data)
        return item


def set_status(task_id: str, status: str) -> dict[str, Any] | None:
    with _LOCK:
        data = _load()
        item = data.get(task_id)
        if item is None:
            return None
        item["status"] = status
        _save(data)
        return item
