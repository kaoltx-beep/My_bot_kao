from __future__ import annotations

from typing import Any, Callable

from core import task_state


class TaskChain:
    """Small persistence-backed sequential chain. No autonomous LLM planner in V1."""

    def __init__(self, max_steps: int = 5) -> None:
        self.max_steps = max(1, min(int(max_steps), 10))

    def run(self, task: str, steps: list[tuple[str, Callable[[], Any]]]) -> dict[str, Any]:
        state = task_state.create(task, max_steps=self.max_steps)
        task_id = state["id"]
        for name, action in steps[: self.max_steps]:
            if task_state.get(task_id)["step"] >= self.max_steps:
                task_state.set_status(task_id, "max_steps")
                break
            try:
                result = action()
                task_state.record_step(task_id, {"tool": name, "success": True, "result": str(result)[:4000]})
            except Exception as exc:
                task_state.record_step(task_id, {"tool": name, "success": False, "error": str(exc)})
                task_state.set_status(task_id, "failed")
                return task_state.get(task_id) or state
        else:
            task_state.set_status(task_id, "completed")
        return task_state.get(task_id) or state
