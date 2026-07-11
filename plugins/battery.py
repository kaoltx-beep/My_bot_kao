import device_actions

METADATA = {
    "name": "battery",
    "description": "ตรวจสอบระดับแบตเตอรี่เครื่อง",
    "keywords": [
        "แบต",
        "แบตเตอรี่",
        "battery",
        "เช็คแบต",
        "ตรวจแบต"
    ]
}


def execute(context=None):
    return device_actions.check_battery()
