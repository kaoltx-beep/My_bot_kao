"""Tool schemas exposed to Hermes."""

GEMINI_STATUS = {
    "name": "gemini_status",
    "description": (
        "Check whether a Google Gemini API key is configured for this Hermes "
        "plugin. Does not send a network request and never reveals the key."
    ),
    "parameters": {"type": "object", "properties": {}, "required": []},
}

GEMINI_CONSULT = {
    "name": "gemini_consult",
    "description": (
        "Send a separate prompt to Google Gemini and return its answer to the "
        "current Hermes session. Use for a second opinion, cross-checking, or "
        "delegating a focused question to Gemini. This does not change Hermes' "
        "primary model. Requires GEMINI_API_KEY or GOOGLE_API_KEY."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "The question or task to send to Gemini."},
            "model": {"type": "string", "description": "Optional Gemini model ID. Defaults to GEMINI_MODEL or gemini-3.8-flash."},
            "system_instruction": {"type": "string", "description": "Optional instructions for Gemini."},
            "temperature": {"type": "number", "description": "Optional creativity setting from 0 to 2."},
            "max_output_tokens": {"type": "integer", "description": "Optional output token limit from 1 to 65536."},
        },
        "required": ["prompt"],
    },
}

GEMINI_LIST_MODELS = {
    "name": "gemini_list_models",
    "description": (
        "List Gemini API models available to the configured API key that "
        "support generateContent. Use this to check model IDs before selecting one."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "max_results": {"type": "integer", "description": "Maximum number of models to return (1 to 50)."}
        },
        "required": [],
    },
}
