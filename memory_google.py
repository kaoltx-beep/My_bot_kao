from google_sheets import connect_google


def save_memory(title, content):
    client = connect_google()

    sheet = client.open("Jarvis_Memory").sheet1

    sheet.append_row([
        title,
        content
    ])

    return True


if __name__ == "__main__":
    save_memory(
        "Test",
        "Jarvis บันทึกความจำผ่าน Google Sheets"
    )

    print("บันทึก Memory สำเร็จ")
