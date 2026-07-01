import re
from device_actions import execute_device_action

def parse_action(raw_answer: str) -> tuple[str, str | None]:
    match = re.search(r"\[\.?ACTION:(.*?)\]", raw_answer)
    action_tag = match.group(1).strip() if match else ""

    clean_answer = re.sub(r"\[\.?ACTION:.*?\]", "", raw_answer).strip()
    action_result = execute_device_action(action_tag)

    return clean_answer, action_result
