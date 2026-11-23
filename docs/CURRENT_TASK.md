Task

Restore Telegram chat ID config compatibility

Progress

90%

Completed

✔ Add TELEGRAM_CHAT_ID environment setting with safe default "0"
✔ Preserve fail-closed Telegram allow-list behavior
✔ Identify three CI errors caused by missing config.TELEGRAM_CHAT_ID

Remaining

- Verify the GitHub Actions run triggered by this commit
- Confirm Telegram security tests pass

Last Update

2026-11-24