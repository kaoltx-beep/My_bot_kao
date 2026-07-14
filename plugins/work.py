from work_logger import save_install_job

METADATA = {
    "name": "work",
    "description": "บันทึกงานติดตั้งลง Google Sheets"
}

def execute(context):
    data = context.get("data", {})

    save_install_job(
        data.get("ลูกค้า", ""),
        data.get("ผู้ให้บริการ", ""),
        data.get("ที่อยู่", ""),
        data.get("สถานะ", ""),
        data.get("หมายเหตุ", "")
    )

    return "บันทึกงานติดตั้งเรียบร้อยแล้ว"
