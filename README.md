# Jarvis AI Assistant — Termux Full Build

รุ่นนี้ใช้ซอร์สจาก Jarvis ตัวเต็มใน Termux เป็นหลัก โดยเก็บการเปลี่ยนแปลงไว้ใน branch แยก ไม่ทับ `main`

## ระบบที่รวมอยู่

- FastAPI: health check และ chat API
- Telegram Bot: เปิด polling เมื่อกำหนด `TELEGRAM_POLLING_ENABLED=1`
- AI Gateway: Groq หรือ Cloudflare Workers AI ตามค่า `AI_PROVIDER`
- LINE webhook
- Field Ops / FOA และระบบจัดการรูปภาพ
- Tool system, memory และ dashboard
- ชุดทดสอบของโปรเจกต์

## เริ่มใช้งานในเครื่อง

ติดตั้ง dependencies:

```bash
python -m pip install -r requirements.txt
```

ตั้งค่าตัวแปรแวดล้อมในเครื่องหรือในระบบโฮสต์ ห้ามอัปโหลด `.env` หรือไฟล์ credential ขึ้น GitHub

เริ่ม API:

```bash
uvicorn run:app --host 0.0.0.0 --port 8000
```

เปิด Telegram polling ด้วย `TELEGRAM_POLLING_ENABLED=1` เฉพาะเมื่อกำหนด Telegram token แล้ว

## ทดสอบ

```bash
python -m pytest -q
```

## Deploy บน Render

Branch สำหรับตรวจสอบและเตรียม deploy:

`termux-full-2026-11-09`

ไฟล์ `deploy/termux_source_bundle.tar.gz.b64` เป็นชุดซอร์สที่คัดเฉพาะไฟล์โค้ดและเอกสาร 157 ไฟล์ ส่วน `prestart.py` จะตรวจ path และแตกชุดซอร์สก่อนเริ่มเว็บเซิร์ฟเวอร์

กำหนด Environment Variables ใน Render แทนการอัปโหลด `.env` เช่น:

- `AI_PROVIDER`
- `GROQ_API_KEY` และ `GROQ_MODEL` หรือค่าของ Cloudflare ตาม provider ที่เลือก
- `TELEGRAM_TOKEN`
- `TELEGRAM_POLLING_ENABLED`
- ค่าของ LINE Messaging API หากต้องการเปิด LINE webhook
- ค่าการเชื่อมต่อ Google Sheets หากเปิดใช้งาน

**ข้อจำกัดก่อนใช้งานจริง:** SQLite และไฟล์ข้อมูลในเครื่องไม่ถูกนำขึ้น GitHub และพื้นที่ดิสก์ของบริการฟรีอาจไม่ถาวร จึงยังไม่ควรใช้ Render เป็นที่เก็บความจำ/ฐานข้อมูลหลัก จนกว่าจะกำหนดที่เก็บข้อมูลถาวรและทดสอบการกู้คืนแล้ว

## ความปลอดภัย

- ไม่รวม `.env`, ฐานข้อมูล, Google credentials, token files, logs หรือไฟล์ backup ใน source bundle
- ห้ามใส่ API key หรือ Telegram/LINE token ลงในซอร์สโค้ด
- ไม่ควรเปิด Telegram polling ซ้ำสองเครื่องด้วย token เดียวกัน
