from datetime import datetime

from google_sheets import connect_google


def save_expense(item, amount, note=""):
    client = connect_google()

    sheet = client.open("Jarvis_Memory").worksheet("Expenses")

    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        item,
        amount,
        note
    ])

    print("บันทึกค่าใช้จ่ายสำเร็จ")


if __name__ == "__main__":
    save_expense(
        item="น้ำมัน",
        amount=500,
        note="ทดสอบระบบ"
    )
