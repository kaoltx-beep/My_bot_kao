import os
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


def get_credentials_path():
    return Path(
        os.getenv(
            "GOOGLE_SERVICE_ACCOUNT_FILE",
            Path(__file__).resolve().parent / "credentials" / "google_service_account.json",
        )
    )


def connect_google():
    credentials_path = get_credentials_path()
    if not credentials_path.exists():
        raise FileNotFoundError(f"ไม่พบ Google service account: {credentials_path}")

    creds = Credentials.from_service_account_file(
        credentials_path,
        scopes=SCOPES
    )
    return gspread.authorize(creds)


def write_test():
    client = connect_google()
    sheet = client.open("Jarvis_Memory").sheet1
    sheet.append_row([
        "Jarvis",
        "เชื่อม Google Sheets สำเร็จ"
    ])
    print("บันทึกข้อมูลสำเร็จ")


if __name__ == "__main__":
    write_test()
