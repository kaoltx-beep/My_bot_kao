import json


def fallback_intent(text):
    text = text.lower()
    if "แบต" in text or "battery" in text:
        return "check_battery"
    if "youtube" in text or "ยูทูป" in text:
        return "open_youtube"
    return None


def process_text(text, history, *, developer_fn, plugin_fn, ai_fn, action_map):
    """Process one Telegram text message through Developer -> Plugin -> AI -> Mobile action."""
    dev_result = developer_fn(text)
    if dev_result:
        return str(dev_result)

    plugin_reply = plugin_fn(text)
    if plugin_reply:
        return plugin_reply

    history_text = "\n".join(f"U:{u} B:{b}" for u, b in history)
    result = ai_fn(text, history_text)
    if not isinstance(result, dict):
        raise ValueError("AI callback must return a dict")

    action = result.get("action") or fallback_intent(text)
    reply = result.get("reply") or "รับทราบ"

    if action and action in action_map:
        try:
            reply = action_map[action]()
        except Exception as exc:
            return f"{reply}\n⚠️ Action Error: {exc}"

    return reply
