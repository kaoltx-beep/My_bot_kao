METADATA = {
    "name": "open_youtube",
    "description": "เปิด YouTube บนอุปกรณ์ Android",
    "category": "device",
    "parameters": ["url", "search_query"]
}


def execute(args=None):
    import device_actions
    return device_actions.open_youtube()
