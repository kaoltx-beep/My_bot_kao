from datetime import datetime

from google_sheets import connect_google


def format_sheet(sheet):
    sheet.format("A1:F1", {
        "textFormat": {"bold": True}
    })
    sheet.freeze(rows=1)
    sheet.columns_auto_resize(0, 6)


def save_install_job(customer, provider, address, status="เสร็จ", note=""):
    client = connect_google()

    sheet = client.open("Jarvis_Memory").worksheet("Install_Jobs")

    if not sheet.row_values(1) or sheet.row_values(1) != ["วันที่", "ลูกค้า", "ผู้ให้บริการ", "ที่อยู่", "สถานะ", "หมายเหตุ"]:
        sheet.insert_row(["วันที่", "ลูกค้า", "ผู้ให้บริการ", "ที่อยู่", "สถานะ", "หมายเหตุ"], 1)
        format_sheet(sheet)

    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        customer,
        provider,
        address,
        status,
        note
    ])

    print("บันทึกงานติดตั้งสำเร็จ")


if __name__ == "__main__":
    save_install_job(
        customer="ทดสอบ",
        provider="True",
        address="ชัยนาท",
        status="เสร็จ",
        note="ทดสอบระบบ"
    )
