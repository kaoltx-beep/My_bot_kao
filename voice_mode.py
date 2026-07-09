import time
import voice_stt
import run


def voice_loop():
    print("🎤 Voice Mode Started")

    while True:
        try:
            text = voice_stt.listen()

            if text:
                print("Voice:", text)

                run.task_queue.put({
                    "chat_id": None,
                    "text": text,
                    "history": []
                })

                time.sleep(5)

            else:
                time.sleep(2)

        except Exception as e:
            print("Voice Error:", e)
            time.sleep(5)


if __name__ == "__main__":
    voice_loop()
