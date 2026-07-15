# Jarvis AI Assistant

ผู้ช่วย AI ส่วนตัวทำงานผ่าน Telegram บน Android (Termux) และ Cloud (Railway)

## Features

- 🤖 **Telegram Bot** — รับคำสั่งและตอบโต้ผ่าน Telegram
- 🧠 **Groq AI** — ใช้ llama-3.1-8b-instant สำหรับการตอบสนอง (JSON mode)
- 🔌 **Plugin System** — battery, expense, task, reminder, news, work, memory, youtube
- 📊 **Google Sheets** — บันทึกงาน, ค่าใช้จ่าย, memory ลง Sheets
- 📱 **MacroDroid** — ควบคุม Android ผ่าน webhook
- 🎤 **Voice** (Termux only) — TTS/STT บน Android
- 🖥️ **Dashboard** — Web dashboard สำหรับดูสถานะ

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/kaoltx-beep/My_bot_kao.git
cd My_bot_kao
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# แก้ไขค่าใน .env ด้วย editor ที่ชอบ
```

ค่าที่ต้องกำหนด:

| Variable | ที่มา | จำเป็น |
|----------|------|-------|
| `TELEGRAM_TOKEN` | [@BotFather](https://t.me/BotFather) | ✅ |
| `TELEGRAM_CHAT_ID` | [@userinfobot](https://t.me/userinfobot) | ✅ |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | ✅ |
| `MACRODROID_WEBHOOK_URL` | MacroDroid app | ❌ optional |
| `GOOGLE_APPLICATION_CREDENTIALS` | Google Cloud Console | ❌ optional |
| `DASHBOARD_TOKEN` | ตั้งเองได้เลย | ❌ optional |

### 4. Google Sheets (optional)

ถ้าต้องการใช้ work logging / expense backup:

1. สร้าง Google Cloud project
2. เปิด Google Sheets API และ Google Drive API
3. สร้าง Service Account และ download JSON key
4. บันทึกไฟล์เป็น `service_account.json` ในโฟลเดอร์โปรเจกต์
5. Share spreadsheet "Jarvis_Memory" ให้กับ service account email

### 5. Run

```bash
python run.py
```

---

## Deployment (Railway)

โปรเจกต์นี้พร้อม deploy บน Railway:

1. สร้าง project ใหม่ใน [Railway](https://railway.app)
2. Connect GitHub repository นี้
3. ตั้ง environment variables ใน Railway dashboard
4. Railway จะ deploy อัตโนมัติจาก `Procfile`

---

## Architecture

```
run.py  (entry point)
├── Telegram Bot (pyTeleBot)
├── Groq AI (llama-3.1-8b-instant)
├── Plugin System (plugins/)
├── Intent Router (intent_router.py)
├── Memory (memory_manager_v2.py + memory_store.py)
├── FastAPI (/status, /pulse, /dashboard, /webhook/feedback)
└── Reminder Worker (background thread)
```

สำหรับ architecture แบบละเอียด ดู [PROJECT_STATUS.md](PROJECT_STATUS.md)

---

## Plugin Commands (ภาษาไทย)

| Plugin | ตัวอย่างคำสั่ง |
|--------|--------------|
| battery | "แบตเหลือเท่าไหร่" |
| expense | "กาแฟ 50", "ดูรายจ่าย", "รายจ่ายเดือนนี้" |
| task | "บันทึกงาน ส่งงานพรุ่งนี้" |
| reminder | "ตั้งเตือน 18:00 ออกกำลังกาย" |
| news | "ข่าววันนี้" |
| memory | "จำว่าฉันชอบกาแฟดำ", "ค้นหา กาแฟ" |
| youtube | "เปิด YouTube" |

---

## Stack

- Python 3.13
- pyTeleBot (Telegram)
- Groq API (AI)
- FastAPI + uvicorn (Web)
- SQLite (local DB)
- gspread (Google Sheets)
- python-dotenv

---

## Security Notes

- Bot ตอบสนองเฉพาะ `TELEGRAM_CHAT_ID` ที่กำหนดเท่านั้น
- ห้าม commit ไฟล์ `.env` หรือ `service_account.json`
- Dashboard `/status` endpoint ป้องกันด้วย `DASHBOARD_TOKEN` (ถ้าตั้งค่า)
- ดูปัญหา security ทั้งหมดใน [TODO.md](TODO.md)

---

## Roadmap

ดู [ROADMAP.md](ROADMAP.md) และ [TODO.md](TODO.md) สำหรับแผนพัฒนาต่อ
