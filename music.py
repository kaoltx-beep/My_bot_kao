import requests

def trigger():
    # แก้ไข URL เรียบร้อยแล้ว
    url = "https://trigger.macrodroid.com/7bb8728a-379b-4377-8e60-8cbd868cfe62/jarvis_open_music_2026"
    try:
        response = requests.get(url, timeout=5)
        print(f"[WEBHOOK] Status: {response.status_code}")
        print(f"[WEBHOOK] Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"[WEBHOOK ERROR] {e}")
        return False
