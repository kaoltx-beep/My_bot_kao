PLUGIN_NAME = "youtube"

import device_actions


def execute(context=None):
    try:
        return device_actions.open_youtube()
    except Exception as e:
        return f"เปิด YouTube ไม่สำเร็จ: {e}"
