"""Google Gemini API handlers. Standard library only; never log API keys."""

import json
import os
import re
import urllib.error
import urllib.request

_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
_DEFAULT_MODEL = "gemini-3.8-flash"
_MODEL_RE = re.compile(r"^[A-Za-z0-9._-]{1,120}$")
_MAX_PROMPT_CHARS = 100_000


def _api_key():
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def _json(data):
    return json.dumps(data, ensure_ascii=False)


def _request(path, payload=None, api_key=None):
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Accept": "application/json", "x-goog-api-key": api_key or _api_key()}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        _API_BASE + path, data=body, headers=headers,
        method="GET" if body is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def gemini_status(args, **kwargs):
    """Report local configuration only; do not reveal any credential."""
    del args, kwargs
    key_name = "GEMINI_API_KEY" if os.environ.get("GEMINI_API_KEY") else (
        "GOOGLE_API_KEY" if os.environ.get("GOOGLE_API_KEY") else None
    )
    return _json({
        "configured": bool(key_name),
        "credential_source": key_name or "missing",
        "default_model": os.environ.get("GEMINI_MODEL", _DEFAULT_MODEL),
        "network_checked": False,
        "message": "API key is configured." if key_name else (
            "No Gemini API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY "
            "in the Hermes .env file, then restart the Hermes gateway."
        ),
    })


def gemini_consult(args, **kwargs):
    """Ask Gemini a question using the Google Generative Language API."""
    del kwargs
    api_key = _api_key()
    if not api_key:
        return _json({
            "success": False, "error": "missing_api_key",
            "message": "Set GEMINI_API_KEY or GOOGLE_API_KEY in the Hermes .env file, then restart Hermes.",
        })

    prompt = args.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return _json({"success": False, "error": "prompt_required"})
    if len(prompt) > _MAX_PROMPT_CHARS:
        return _json({"success": False, "error": "prompt_too_long", "max_characters": _MAX_PROMPT_CHARS})

    model = args.get("model") or os.environ.get("GEMINI_MODEL", _DEFAULT_MODEL)
    if not isinstance(model, str) or not _MODEL_RE.fullmatch(model):
        return _json({"success": False, "error": "invalid_model_id"})

    generation_config = {}
    temperature = args.get("temperature")
    if temperature is not None:
        if not isinstance(temperature, (int, float)) or isinstance(temperature, bool) or not 0 <= temperature <= 2:
            return _json({"success": False, "error": "temperature_must_be_between_0_and_2"})
        generation_config["temperature"] = float(temperature)

    max_tokens = args.get("max_output_tokens")
    if max_tokens is not None:
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or not 1 <= max_tokens <= 65536:
            return _json({"success": False, "error": "max_output_tokens_must_be_between_1_and_65536"})
        generation_config["maxOutputTokens"] = max_tokens

    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    system_instruction = args.get("system_instruction")
    if isinstance(system_instruction, str) and system_instruction.strip():
        payload["systemInstruction"] = {"parts": [{"text": system_instruction[:10000]}]}
    if generation_config:
        payload["generationConfig"] = generation_config

    try:
        data = _request("/models/" + model + ":generateContent", payload, api_key=api_key)
        candidates = data.get("candidates") or []
        parts = (candidates[0].get("content") or {}).get("parts") or [] if candidates else []
        answer = "\n".join(
            part.get("text", "") for part in parts
            if isinstance(part, dict) and part.get("text")
        )
        if not answer:
            return _json({
                "success": False, "model": model, "error": "empty_response",
                "finish_reason": candidates[0].get("finishReason") if candidates else None,
            })
        usage = data.get("usageMetadata") or {}
        return _json({
            "success": True, "provider": "Google Gemini API", "model": model,
            "answer": answer,
            "usage": {
                "prompt_tokens": usage.get("promptTokenCount"),
                "output_tokens": usage.get("candidatesTokenCount"),
                "total_tokens": usage.get("totalTokenCount"),
            },
        })
    except urllib.error.HTTPError as exc:
        detail = "Google Gemini API returned HTTP " + str(exc.code)
        try:
            body = json.loads(exc.read().decode("utf-8"))
            message = (body.get("error") or {}).get("message")
            if message:
                detail += ": " + str(message)[:1200]
        except Exception:
            pass
        return _json({"success": False, "model": model, "error": detail})
    except urllib.error.URLError as exc:
        return _json({"success": False, "model": model, "error": "network_error", "detail": str(exc.reason)[:500]})
    except Exception as exc:
        return _json({"success": False, "model": model, "error": "request_failed", "detail": str(exc)[:500]})


def gemini_list_models(args, **kwargs):
    """List models available to this key that support generateContent."""
    del kwargs
    api_key = _api_key()
    if not api_key:
        return _json({"success": False, "error": "missing_api_key"})
    limit = args.get("max_results", 30)
    if not isinstance(limit, int) or isinstance(limit, bool):
        limit = 30
    limit = max(1, min(limit, 50))
    try:
        data = _request("/models?pageSize=100", api_key=api_key)
        models = []
        for item in data.get("models", []):
            if "generateContent" not in item.get("supportedGenerationMethods", []):
                continue
            models.append({
                "name": item.get("name", "").removeprefix("models/"),
                "display_name": item.get("displayName"),
                "input_token_limit": item.get("inputTokenLimit"),
                "output_token_limit": item.get("outputTokenLimit"),
            })
            if len(models) >= limit:
                break
        return _json({"success": True, "count": len(models), "models": models})
    except urllib.error.HTTPError as exc:
        return _json({"success": False, "error": "Google Gemini API returned HTTP " + str(exc.code)})
    except urllib.error.URLError as exc:
        return _json({"success": False, "error": "network_error", "detail": str(exc.reason)[:500]})
    except Exception as exc:
        return _json({"success": False, "error": "request_failed", "detail": str(exc)[:500]})
