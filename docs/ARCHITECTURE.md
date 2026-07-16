# Architecture Overview

This document outlines the architectural components and their interactions within the Jarvis project.

## Core Components

### 1. Telegram Bot Interface
- **Entry Point:** `run.py` handles incoming messages from Telegram.
- **Security:** Filters messages based on `TELEGRAM_CHAT_ID` for authorized users.
- **Asynchronous Processing:** Messages are queued into a `task_queue` and processed by a separate `worker` thread.

### 2. AI Core (Groq Integration)
- **Main Logic:** `ask_jarvis` function in `run.py` interacts with the Groq API.
- **Model:** Currently uses `llama-3.1-8b-instant`.
- **Response Format:** Expects and processes JSON responses for `reply` and `action`.
- **Context Management:** Integrates chat history and memory from `memory_manager_v2` to enrich AI prompts.

### 3. Plugin System
- **Dynamic Loading:** `plugin_loader.py` dynamically loads plugins from the `plugins/` directory.
- **Plugin Mapping:** `PLUGIN_MAP` in `run.py` maps detected actions to specific plugin names.
- **Execution:** Plugins are executed via `plugin.execute(text)`.
- **Examples:** Includes plugins for battery, YouTube, news, expense, task, reminder, and work.

### 4. Memory Management
- **Module:** `memory_manager_v2.py` manages conversational memory.
- **Storage:** Uses SQLite (`jarvis_memory.db`) for local persistence.
- **Backup:** Integrates with `google_sheets.py` for optional Google Sheets backup of memory.

### 5. Data Storage
- **SQLite Databases:** Multiple SQLite databases are used for various modules:
    - `jarvis_memory.db` (for `memory_manager_v2`)
    - `expense.db` (for `expense_manager`)
    - `jobs.db` (for `job_database`)
    - `reminder.db` (for `reminder_manager` and `reminder_worker`)
    - `task.db` (for `task_manager`)
    - `chat_history.db` (for `feedback_server`)

### 6. FastAPI Web Server
- **Endpoints:** Provides `/pulse`, `/status`, and `/webhook/feedback`.
- **Dashboard:** Serves a static dashboard from the `dashboard/` directory.
- **Authentication:** `_check_dashboard_auth` function exists but is not currently applied to any routes, indicating a potential security oversight.

### 7. Background Workers
- **Main Worker:** Processes tasks from `task_queue` (AI responses, plugin execution).
- **Reminder Worker:** `reminder_worker.py` runs in a separate thread to send scheduled reminders.
- **Voice Worker (Commented Out):** `voice_worker` for speech-to-text input is present but currently disabled.

## External Integrations
- **Groq API:** For AI model inference.
- **Telegram Bot API:** For user interaction.
- **Google Sheets API:** For memory backup and potentially other data logging (via `gspread`).
- **MacroDroid Webhook:** For receiving feedback or triggers from Android devices.

## Dependencies (from `requirements.txt`)
- `python-telegram-bot`
- `groq`
- `fastapi`
- `uvicorn`
- `requests`
- `python-dotenv` (implied by `load_dotenv()` in `config.py`)
- `gspread` (implied by `google_sheets.py`)
- `google-auth-oauthlib` (implied by `google_sheets.py`)
- `google-api-python-client` (implied by `google_sheets.py`)

## Workflow
User input (Telegram/Voice) -> `task_queue` -> `worker` thread -> `ask_jarvis` (Groq) -> `intent_router`/`fallback_intent`/`PLUGIN_MAP` -> Plugin execution / Direct reply -> `memory_manager.save_memory` -> Telegram/TTS output.
