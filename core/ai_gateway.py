"""Single AI Gateway for Jarvis.

All provider access should go through this module. Callers receive plain text;
JSON mode is only a response-format hint and does not change the return type.
"""

import os
from typing import Any, Dict, List, Optional

from groq import Groq


class AIGatewayError(RuntimeError):
    """Normalized AI gateway failure."""


class AIGateway:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, timeout: float = 60.0):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model or os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        self.timeout = timeout
        self._client = None

    @property
    def client(self) -> Groq:
        if not self.api_key:
            raise AIGatewayError("GROQ_API_KEY is not configured")
        if self._client is None:
            self._client = Groq(api_key=self.api_key, timeout=self.timeout)
        return self._client

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        """Send one chat request and return normalized text content."""
        kwargs: Dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            if not content:
                raise AIGatewayError("AI returned an empty response")
            return content
        except AIGatewayError:
            raise
        except Exception as exc:
            raise AIGatewayError(str(exc)) from exc

    def status(self) -> Dict[str, Any]:
        return {
            "provider": "groq",
            "model": self.model,
            "configured": bool(self.api_key),
        }


_default_gateway: Optional[AIGateway] = None


def get_gateway() -> AIGateway:
    global _default_gateway
    if _default_gateway is None:
        _default_gateway = AIGateway()
    return _default_gateway
