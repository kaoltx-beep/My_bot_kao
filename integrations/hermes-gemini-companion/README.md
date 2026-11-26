# Hermes Gemini Companion

A native Hermes Agent plugin that lets the active Hermes model consult Google Gemini as a separate model.

**Important:** Hermes already has a built-in `gemini` provider for using Gemini as the primary model. This plugin does not replace that provider or change the selected Hermes model. It adds three optional tools so Hermes can check Gemini credentials, ask Gemini for a second opinion, and list models available to the API key.

## Tools

- `gemini_status` — checks whether a key is configured without revealing it or making a network request.
- `gemini_consult` — sends a prompt to Gemini and returns its answer.
- `gemini_list_models` — lists models available to the configured key that support `generateContent`.

## Requirements

- Hermes Agent with native Python plugin support.
- Python standard library only; no extra pip packages.
- A Google Gemini API key from Google AI Studio.

## Install on Windows

Copy this directory to:

```powershell
$env:LOCALAPPDATA\hermes\plugins\gemini-companion
```

Then enable it with the Hermes CLI:

```powershell
hermes plugins enable gemini-companion
hermes plugins list
```

Restart the Hermes gateway after enabling the plugin.

## Configure the key safely

Run `Set-GeminiApiKey.ps1` in PowerShell. It prompts for the key without echoing it, backs up the existing Hermes `.env` file, and writes only the `GEMINI_API_KEY` entry. The key is never included in GitHub files or printed by the plugin.

The plugin also accepts `GOOGLE_API_KEY` as a fallback. An optional `GEMINI_MODEL` environment variable changes the default model. The default is `gemini-3.8-flash`; use `gemini_list_models` to verify the models available to your key.

## Example

Ask Hermes: "Use Gemini to independently review this Python function and list any bugs."

Hermes calls `gemini_consult` and presents Gemini's response in the current conversation. This makes a separate API request and may incur Google API usage or charges according to the user's Google AI Studio project.

## Security

- Credentials are read only from environment variables.
- The API key is sent in the `x-goog-api-key` HTTP header, not in the URL.
- No credential or prompt logging is performed by this plugin.
- No key is included in this repository.
