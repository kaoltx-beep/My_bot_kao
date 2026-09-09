import unittest

from core.pipeline import process_text


class PipelineTests(unittest.TestCase):
    def test_ai_to_mobile_action(self):
        calls = []

        def developer(text):
            calls.append("developer")
            return None

        def plugin(text):
            calls.append("plugin")
            return None

        def ai(text, history):
            calls.append(("ai", history))
            return {"reply": "กำลังเปิด", "action": "open_youtube"}

        def open_youtube():
            calls.append("mobile")
            return "📺 เปิด YouTube แล้ว"

        reply = process_text(
            "เปิดยูทูป",
            [("ก่อนหน้า", "ตอบก่อนหน้า")],
            developer_fn=developer,
            plugin_fn=plugin,
            ai_fn=ai,
            action_map={"open_youtube": open_youtube},
        )

        self.assertEqual(reply, "📺 เปิด YouTube แล้ว")
        self.assertEqual(calls[0:2], ["developer", "plugin"])
        self.assertEqual(calls[2][0], "ai")
        self.assertIn("U:ก่อนหน้า B:ตอบก่อนหน้า", calls[2][1])
        self.assertEqual(calls[3], "mobile")

    def test_plugin_short_circuits_ai(self):
        calls = []

        reply = process_text(
            "งาน",
            [],
            developer_fn=lambda text: None,
            plugin_fn=lambda text: calls.append("plugin") or "plugin-result",
            ai_fn=lambda text, history: calls.append("ai") or {"reply": "ai-result"},
            action_map={},
        )

        self.assertEqual(reply, "plugin-result")
        self.assertEqual(calls, ["plugin"])

    def test_developer_short_circuits_everything(self):
        calls = []

        reply = process_text(
            "แก้โค้ด",
            [],
            developer_fn=lambda text: calls.append("developer") or "confirm-first",
            plugin_fn=lambda text: calls.append("plugin") or None,
            ai_fn=lambda text, history: calls.append("ai") or {"reply": "ai-result"},
            action_map={},
        )

        self.assertEqual(reply, "confirm-first")
        self.assertEqual(calls, ["developer"])

    def test_action_failure_does_not_kill_pipeline(self):
        def broken_action():
            raise RuntimeError("mobile unavailable")

        reply = process_text(
            "เปิดยูทูป",
            [],
            developer_fn=lambda text: None,
            plugin_fn=lambda text: None,
            ai_fn=lambda text, history: {"reply": "จะเปิดให้", "action": "open_youtube"},
            action_map={"open_youtube": broken_action},
        )

        self.assertIn("จะเปิดให้", reply)
        self.assertIn("Action Error", reply)


if __name__ == "__main__":
    unittest.main()
