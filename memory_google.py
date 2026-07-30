import os
from pathlib import Path

from google_sheets import connect_google


def save_memory(title, content):
    """Best-effort Google Sheets memory backup.

    Local SQLite memory remains the source of truth. If the service-account
    credential file is not present, skip the remote backup quietly.
    """
    credentials_path = Path(
        os.getenv(
            "GOOGLE_SERVICE_ACCOUNT_FILE",
            Path(__file__).resolve().parent / "credentials" / "google_service_account.json",
        )
    )
    if not credentials_path.exists():
        return False

    client = connect_google()
    sheet = client.open("Jarvis_Memory").sheet1
    sheet.append_row([title, content])
    return True


if __name__ == "__main__":
    result = save_memory(
        "Test",
        "Jarvis บันทึกความจำผ่าน Google Sheets"
    )
    print("บันทึก Memory สำเร็จ" if result else "Google Memory Backup ยังไม่ได้ตั้งค่า")
