import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return self.payload


class GeminiToolsTests(unittest.TestCase):
    def test_status_never_returns_key(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "do-not-leak"}, clear=True):
            result = json.loads(tools.gemini_status({}))
        self.assertTrue(result["configured"])
        self.assertNotIn("do-not-leak", json.dumps(result))

    def test_consult_success(self):
        payload = {"candidates": [{"content": {"parts": [{"text": "สวัสดี"}]}}]}
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
            with patch.object(tools.urllib.request, "urlopen", return_value=FakeResponse(payload)) as call:
                result = json.loads(tools.gemini_consult({"prompt": "ทดสอบ"}))
        self.assertTrue(result["success"])
        self.assertEqual(result["answer"], "สวัสดี")
        self.assertNotIn("test-key", call.call_args.args[0].full_url)

    def test_missing_key_does_not_call_network(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(tools.urllib.request, "urlopen") as call:
                result = json.loads(tools.gemini_consult({"prompt": "test"}))
        self.assertFalse(result["success"])
        call.assert_not_called()

    def test_invalid_model_is_rejected(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
            with patch.object(tools.urllib.request, "urlopen") as call:
                result = json.loads(tools.gemini_consult({"prompt": "test", "model": "../bad"}))
        self.assertEqual(result["error"], "invalid_model_id")
        call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
