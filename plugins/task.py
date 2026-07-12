import task_manager

PLUGIN_NAME = "task"


def execute(text=None):
    if not text:
        return "❌ ไม่พบข้อมูล"

    text = text.lower()

    if "วันนี้มีงาน" in text or "ดูงาน" in text or "รายการงาน" in text:
        return task_manager.list_tasks()

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
