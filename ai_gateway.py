"""Single Groq-compatible gateway for Jarvis text and Vision requests."""

from __future__ import annotations

import base64
import os
from typing import Any, Callable

import requests

import config


GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
CLOUDFLARE_RUN_URL = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
DEFAULT_TEXT_MODEL = "openai/gpt-oss-20b"
DEFAULT_VISION_MODEL = "qwen/qwen3.6-27b"


def _gateway_request(
    messages: list[dict[str, Any]],
    *,
    model: str,
    timeout: int = 60,
    retries: int = 0,
    request_post: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Send one request through the only supported AI provider path."""
    provider = (getattr(config, "AI_PROVIDER", None) or os.getenv("AI_PROVIDER", "groq")).strip().lower()
    if provider == "cloudflare":
        api_key = (getattr(config, "CLOUDFLARE_API_TOKEN", None) or os.getenv("CLOUDFLARE_API_TOKEN") or "").strip()
        account_id = (getattr(config, "CLOUDFLARE_ACCOUNT_ID", None) or os.getenv("CLOUDFLARE_ACCOUNT_ID") or "").strip()
        cf_model = (getattr(config, "CLOUDFLARE_AI_MODEL", None) or os.getenv("CLOUDFLARE_AI_MODEL") or "@cf/meta/llama-3.1-8b-instruct").strip()
        if not api_key or not account_id:
            return {"status": "error", "reply": "", "message": "Cloudflare ยังตั้งค่าไม่ครบ ต้องมี CLOUDFLARE_API_TOKEN และ CLOUDFLARE_ACCOUNT_ID"}
        url = CLOUDFLARE_RUN_URL.format(account_id=account_id, model=cf_model)
        payload = {"messages": messages, "max_tokens": 512, "temperature": 0.2}
        provider_name = "cloudflare"
    else:
        api_key = (getattr(config, "GROQ_API_KEY", None) or os.getenv("GROQ_API_KEY") or "").strip()
        if not api_key:
            return {"status": "error", "reply": "", "message": "ยังไม่ได้ตั้งค่า GROQ_API_KEY สำหรับ AI Gateway"}
        url = GROQ_CHAT_URL
        payload = {"model": model, "messages": messages, "temperature": 0.2}
        provider_name = "groq"

    post = request_post or requests.post
    for attempt in range(max(0, retries) + 1):
        try:
            response = post(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            if provider_name == "cloudflare":
                result = data.get("result") or {}
                reply = str(result.get("response") or result.get("output") or "").strip()
            else:
                reply = str(data["choices"][0]["message"]["content"]).strip()
            if not reply:
                raise ValueError("provider returned an empty reply")
            return {"status": "success", "reply": reply, "model": cf_model if provider_name == "cloudflare" else model, "provider": provider_name}
        except requests.Timeout:
            if attempt < max(0, retries):
                continue
            return {"status": "error", "reply": "", "message": "AI Gateway ใช้เวลาตอบนานเกินกำหนด กรุณาลองใหม่อีกครั้ง"}
        except requests.HTTPError as exc:
            status_code = getattr(exc.response, "status_code", "unknown")
            return {"status": "error", "reply": "", "message": f"AI Gateway ตอบกลับผิดพลาด (HTTP {status_code})"}
        except Exception as exc:
            return {"status": "error", "reply": "", "message": f"AI Gateway ใช้งานไม่ได้: {type(exc).__name__}"}

    raise RuntimeError("unreachable gateway retry state")


def ask_text(
    prompt: str,
    memory: list[Any] | None = None,
    *,
    request_post: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Get a text response while preserving existing Jarvis memory behavior."""
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "คุณคือ Jarvis ผู้ช่วย AI ส่วนตัว ตอบภาษาเดียวกับผู้ใช้ "
                "ตอบกระชับ ชัดเจน และใช้บริบทความจำเมื่อมีให้"
            ),
        }
    ]
    if memory:
        context = "\n".join(f"ผู้ใช้: {row[0]}\nJarvis: {row[1]}" for row in memory)
        messages.append({"role": "system", "content": "บริบทความจำล่าสุดของ Jarvis:\n" + context})
    messages.append({"role": "user", "content": prompt})
    model = (getattr(config, "GROQ_MODEL", None) or os.getenv("GROQ_MODEL") or DEFAULT_TEXT_MODEL).strip() or DEFAULT_TEXT_MODEL
    return _gateway_request(messages, model=model, request_post=request_post)


def ask_vision(
    prompt: str,
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    *,
    retries: int | None = None,
    request_post: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Analyze a local image through the same gateway using a configured vision model."""
    if not image_bytes:
        return {"status": "error", "reply": "", "message": "ไฟล์รูปภาพว่างเปล่า"}

    encoded = base64.b64encode(image_bytes).decode("ascii")
    model = (getattr(config, "GROQ_VISION_MODEL", None) or os.getenv("GROQ_VISION_MODEL") or DEFAULT_VISION_MODEL).strip() or DEFAULT_VISION_MODEL
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "คุณคือผู้ช่วย Jarvis Field Ops วิเคราะห์ภาพหน้างาน "
                "ตอบภาษาไทย ระบุสิ่งที่สังเกตได้อย่างระมัดระวัง "
                "อย่ายืนยันสิ่งที่ภาพไม่ชัด และเสนอข้อมูลที่ต้องเก็บเพิ่ม"
            ),
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
                },
            ],
        },
    ]
    configured_retries = retries if retries is not None else int(os.getenv("GROQ_VISION_RETRIES", "1"))
    return _gateway_request(
        messages,
        model=model,
        timeout=75,
        retries=max(0, configured_retries),
        request_post=request_post,
    )
