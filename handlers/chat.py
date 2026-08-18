"""Shared Jarvis chat pipeline: tools -> memory -> AI -> memory."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1)


_tool_system: Any = None
_ai_callback: Any = None


def configure(ai_callback: Any, tool_system: Any = None) -> None:
    global _ai_callback, _tool_system
    _ai_callback = ai_callback
    _tool_system = tool_system


def _format_tool_result(result: Any) -> str:
    if result is None:
        return "ดำเนินการสำเร็จ"
    if getattr(result, "success", False):
        data = getattr(result, "data", None)
        return str(data) if data is not None else "ดำเนินการสำเร็จ"
    return f"ดำเนินการไม่สำเร็จ: {getattr(result, 'error', 'unknown error')}"


def _save_memory(prompt: str, reply: str) -> None:
    try:
        import memory_manager_v2
        memory_manager_v2.save_memory(prompt, reply)
    except Exception as exc:
        print("Memory save failed:", exc)


def process_message(prompt: str) -> dict[str, Any]:
    text = (prompt or "").strip()
    if not text:
        return {"status": "error", "message": "prompt must not be empty"}

    # 1) Deterministic tool routing. ToolExecutor remains the safety gate.
    if _tool_system is not None:
        call = _tool_system.parse(text)
        if call is not None:
            result = _tool_system.execute(call.tool_name, call.params, approved=False)
            reply = _format_tool_result(result)
            _save_memory(text, reply)
            return {
                "status": "success" if getattr(result, "success", False) else "error",
                "reply": reply,
                "tool": call.tool_name,
                "tool_result": {
                    "success": getattr(result, "success", False),
                    "data": getattr(result, "data", None),
                    "error": getattr(result, "error", None),
                    "duration_ms": getattr(result, "duration_ms", 0),
                },
            }

    # 2) Load recent memory as context for the AI path.
    memory = []
    try:
        import memory_manager_v2
        memory = memory_manager_v2.get_memory(5)
    except Exception as exc:
        print("Memory read failed:", exc)

    if _ai_callback is None:
        raise RuntimeError("Jarvis AI gateway is not configured")

    result = _ai_callback(text, memory)
    if not isinstance(result, dict):
        result = {"status": "success", "reply": str(result)}

    # 3) Persist the conversation after the AI response.
    reply = str(result.get("reply", ""))
    if reply:
        _save_memory(text, reply)

    response: dict[str, Any] = {
        "status": result.get("status", "success"),
        "reply": reply,
        "memory_used": len(memory),
    }
    for key in ("message", "model"):
        if result.get(key):
            response[key] = result[key]
    return response


@router.post("/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    try:
        return process_message(request.prompt)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
