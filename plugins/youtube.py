import device_actions

METADATA = {
    "name": "youtube",
    "description": "เปิดแอป YouTube บนอุปกรณ์",
    "keywords": [
        "youtube",
        "ยูทูป",
        "เปิดยูทูป",
        "เปิด youtube"
    ]
}


def execute(context=None):
    try:
        return device_actions.open_youtube()
    except Exception as e:
        return f"เปิด YouTube ไม่สำเร็จครับ: {e}"
