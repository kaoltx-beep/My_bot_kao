import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(
    "credentials/google_service_account.json",
    scopes=SCOPES
)

client = gspread.authorize(creds)

print("Google Sheets เชื่อมต่อสำเร็จ")
