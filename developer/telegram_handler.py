class TelegramCommandHandler:
    def __init__(
        self,
        bot=None,
        router=None,
        agent=None,
        patcher=None,
        sessions=None,
        logger=None,
        git=None
    ):
        self.bot = bot
        self.router = router
        self.agent = agent
        self.patcher = patcher
        self.sessions = sessions
        self.logger = logger
        self.git = git

    def handle_command(self, text, *args):
        if text.startswith("/dev_analyze"):
            target = text.replace("/dev_analyze", "").strip()
            return {
                "message": f"🔍 Analyze: {target}\\n"
                           f"พร้อมวิเคราะห์ไฟล์"
            }

        if text.startswith("/dev_generate"):
            return {
                "message": "🔧 Generate: รับคำสั่งสร้างไฟล์แล้ว"
            }

        if text.startswith("/dev_status"):
            return {
                "message": "🟢 Developer Mode Ready"
            }

        if text.startswith("/dev_approve"):
            return {
                "message": "✅ Approved"
            }

        if self.router:
            result = self.router.handle_developer_request(text)
            return {
                "message": result or "ไม่มีผลลัพธ์"
            }

        return {
            "message": "router unavailable"
        }

    def send_approval(self, message):
        return {
            "status": "waiting",
            "message": message
        }

    def approve(self, session_id):
        return {
            "status": "approved",
            "session_id": session_id
        }

    def reject(self, session_id):
        return {
            "status": "rejected",
            "session_id": session_id
        }
