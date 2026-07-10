METADATA = {
    "name": "check_battery",
    "description": "ตรวจสอบระดับแบตเตอรี่ของมือถือ",
    "category": "device",
    "parameters": []
}


def execute(args=None):
    import device_actions
    return device_actions.check_battery()
