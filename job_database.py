import sqlite3
from datetime import datetime, timedelta

DB = "jobs.db"


def is_duplicate(customer, provider, address):
    today = datetime.now().strftime("%Y-%m-%d")
    db = sqlite3.connect(DB)
    result = db.execute(
        """
        SELECT id FROM jobs
        WHERE date LIKE ?
        AND customer=?
        AND provider=?
        AND address=?
        """,
        (today + "%", customer, provider, address),
    ).fetchone()
    db.close()
    return result is not None


def save_job(customer, provider, address, status, note):
    db = sqlite3.connect(DB)
    db.execute(
        """
        INSERT INTO jobs
        (date, customer, provider, address, status, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            customer,
            provider,
            address,
            status,
            note,
        ),
    )
    db.commit()
    db.close()


def list_jobs():
    db = sqlite3.connect(DB)
    rows = db.execute(
        """
        SELECT customer, provider, address, status
        FROM jobs
        ORDER BY id DESC
        LIMIT 10
        """
    ).fetchall()
    db.close()
    if not rows:
        return "ยังไม่มีข้อมูลงานครับ"
    result = "📋 งานล่าสุด\n"
    for r in rows:
        result += f"- {r[0]} | {r[1]} | {r[2]} | {r[3]}\n"
    return result


def search_jobs(area):
    db = sqlite3.connect(DB)
    rows = db.execute(
        """
        SELECT customer, provider, address, status
        FROM jobs
        WHERE address LIKE ?
        ORDER BY id DESC
        """,
        (f"%{area}%",),
    ).fetchall()
    db.close()
    if not rows:
        return f"ไม่พบงานที่ {area} ครับ"
    result = f"📍 งานที่ {area}\n"
    for r in rows:
        result += f"- {r[0]} | {r[1]} | {r[3]}\n"
    return result


def pending_jobs():
    db = sqlite3.connect(DB)
    rows = db.execute(
        """
        SELECT customer, provider, address, status
        FROM jobs
        WHERE status NOT LIKE '%เสร็จ%'
        ORDER BY id DESC
        """
    ).fetchall()
    db.close()
    if not rows:
        return "ไม่มีงานค้างครับ"
    result = "📌 งานที่ยังไม่เสร็จ\n"
    for r in rows:
        result += f"- {r[0]} | {r[1]} | {r[2]} | {r[3]}\n"
    return result


def tomorrow_jobs():
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    db = sqlite3.connect(DB)
    rows = db.execute(
        """
        SELECT customer, provider, address, status
        FROM jobs
        WHERE date LIKE ?
        ORDER BY id ASC
        """,
        (tomorrow + "%",),
    ).fetchall()
    db.close()

    if not rows:
        return "พรุ่งนี้ยังไม่มีงานที่บันทึกไว้ครับ"

    result = "📅 งานพรุ่งนี้\n"
    for r in rows:
        result += f"- {r[0]} | {r[1]} | {r[2]} | {r[3]}\n"
    return result.rstrip()
