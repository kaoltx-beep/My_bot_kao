import task_manager
import work_logger

PLUGIN_NAME = "task"


def execute(text=None):
    if not text:
        return "❌ ไม่พบข้อมูล"

    text = text.lower()

    if "วันนี้มีงาน" in text or "ดูงาน" in text or "รายการงาน" in text:
        return task_manager.list_tasks()

    if any(x in text for x in ["ติดตั้ง", "ไฟเบอร์", "fiber", "3bb", "true", "ais"]):
        provider = "ไม่ระบุ"
        customer = "ไม่ระบุ"
        address = "ไม่ระบุ"

        for x in ["true", "3bb", "ais"]:
            if x in text:
                provider = x.upper()

        if "ลูกค้า" in text:
            customer = text.split("ลูกค้า")[-1].split("ที่")[0].strip()

        if "ที่" in text:
            address = text.split("ที่")[-1].replace("เสร็จแล้ว", "").strip()

        work_logger.save_install_job(
            customer=customer,
            provider=provider,
            address=address,
            status="เสร็จแล้ว",
            note=text
        )
        return "✅ บันทึกงานติดตั้งเข้า Google Sheets แล้วครับ"

    words = [
        "บันทึกงาน",
        "เพิ่มงาน",
    ]

    task = text

    for w in words:
        task = task.replace(w, "").strip()

    if not task:
        return "❌ ตัวอย่าง: บันทึกงาน ส่งเอกสาร"

    return task_manager.add_task(task)
