import voice_stt
import run
import time

print("🎤 พร้อมรับเสียง")

text = voice_stt.listen()

if text:
    print("ได้ยิน:", text)

    run.task_queue.put({
        "chat_id": None,
        "text": text,
        "history": []
    })

    print("ส่งให้ Jarvis แล้ว")
else:
    print("ไม่ได้ยินเสียง")
