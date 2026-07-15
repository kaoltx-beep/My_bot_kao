from work_logger import save_install_job
from work_extractor import extract_work
from job_database import is_duplicate, save_job
from work_extractor import extract_work

def is_install_work(text):
    keywords = [
        "ติดตั้ง",
        "เดินสาย",
        "ไฟเบอร์",
        "fiber",
        "ลูกค้า",
        "หน้างาน"
    ]

    return any(k in text.lower() for k in keywords)


def save_auto_work(text):
    if not is_install_work(text):
        return False

    data = extract_work(text)

    if is_duplicate(
        data["customer"],
        data["provider"],
        data["address"]
    ):
        return "duplicate"

    save_job(
        data["customer"],
        data["provider"],
        data["address"],
        data["status"],
        data["note"]
    )

    save_install_job(
        customer=data["customer"],
        provider=data["provider"],
        address=data["address"],
        status=data["status"],
        note=data["note"]
    )
    return True
