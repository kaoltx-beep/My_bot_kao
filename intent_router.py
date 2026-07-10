def classify(text):
    text = text.lower()

    intents = {
        "check_battery": ["แบต", "battery", "แบตเตอรี่"],
        "open_youtube": ["youtube", "ยูทูป", "เปิดเพลง"],
    }

    for action, keywords in intents.items():
        for word in keywords:
            if word in text:
                return action

    return None
