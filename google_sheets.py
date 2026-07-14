import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


def connect_google():
    creds = Credentials.from_service_account_file(
        "credentials/google_service_account.json",
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
