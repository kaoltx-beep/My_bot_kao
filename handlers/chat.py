"""HTTP chat endpoint for Jarvis.

The actual application callback is injected by run.py so this module stays
independent from the Telegram transport and can be tested in isolation.
"""

from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1)


_chat_callback: Callable[[str], Any] | None = None


def configure(callback: Callable[[str], Any]) -> None:
    global _chat_callback
    _chat_callback = callback


@router.post("/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    if _chat_callback is None:
        raise HTTPException(status_code=503, detail="Jarvis chat handler is not configured")

    try:
        result = _chat_callback(request.prompt)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if isinstance(result, dict):
        return result
    return {"status": "success", "reply": str(result)}
