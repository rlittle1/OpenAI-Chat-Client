# OpenAI Chat Client (Tkinter)

A simple desktop GUI chat client for OpenAI models built with Python and Tkinter. It provides a minimal, local chat interface with chat history, export, theme toggle, and an integrated API-key setup dialog. Chats are saved locally to your Documents folder.

> Note: This client uses the OpenAI Python SDK (OpenAI class) and requires a valid OpenAI API key to work.

## Features
- Chat with OpenAI models (selectable from UI)
- Save and load conversation history (auto-saved)
- Generate short chat titles automatically from the first user prompt
- Export chats to plain text / markdown files (single or batch)
- Rename and delete chats from a list
- Copy entire conversation to clipboard
- Light / Dark mode toggle
- API key entry dialog with validation and optional .env persistence
- Autosave every 5 seconds (when not processing)

## Requirements
- Python 3.8+ (3.10+ recommended)
- Tkinter (usually included with Python on Windows/macOS; on some Linux installs you may need `python3-tk`)
- openai Python package (newer SDK exposing `OpenAI` class)

## Installation

1. Clone the repository
   ```
   git clone https://github.com/rlittle1/OpenAI-Chat-Client.git
   cd OpenAI-Chat-Client
   ```
2. (Optional) Create and activate a virtual environment
   python -m venv venv
   # Windows
   ```
   venv\Scripts\activate
   ```

   # macOS / Linux
   ```
   source venv/bin/activate
   ```

4. Install dependencies
   ```
   pip install openai
   ```

5. Place the script in the repo (for example `chat_client.py`) — the GUI code in this repository assumes the OpenAI SDK is available as `from openai import OpenAI`.

## Running

Run the app:
```
python chat_client.py
```

On first run the app will ask whether you'd like to set your API key. You can:
- Set the `OPENAI_API_KEY` environment variable before starting the app, or
- Enter your API key via Settings → Set API Key… in the app UI

When saving via the dialog the key is kept in the current session and the app will attempt to persist it to a `.env` file in the working directory (this is optional and may fail based on filesystem permissions).

## API Key

Obtain your API key at: [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)

You can provide it in one of two ways:
- Environment variable:
  - Linux/macOS: export OPENAI_API_KEY="sk-..."
  - Windows (PowerShell): $env:OPENAI_API_KEY="sk-..."
- In-app Settings → Set API Key… (the dialog tests the key before accepting it)

Security note: Do not share your API key. If saving to a `.env` file, ensure the file is not accidentally committed to version control (add to `.gitignore`).

Example `.env`:
OPENAI_API_KEY=sk-...

## Where chats are saved

Chats are saved as JSON files in:
- {HOME}/Documents/chats

Each conversation is saved as `<title>.json`. The app creates this folder automatically if it doesn't exist.

## Supported models

The code includes a model selector with defaults such as:
- gpt-5-nano
- gpt-5-mini (default)
- gpt-5
- gpt-4.1-nano
- gpt-4.1-mini
- gpt-4.1

You may edit the `models` list in the script to match the available models in your OpenAI account. Note that using larger models can increase cost and latency.

## Usage highlights
- Enter text in the bottom input area. Press Enter to send (Shift+Enter for newline).
- New Chat starts a fresh conversation.
- Right-click chats in the left list to rename, export, or delete.
- Export allows saving conversation text files or batch export to a folder.
- Dark Mode toggle available in the header or Settings → Toggle Dark Mode.
- Conversations auto-save every 5 seconds when idle and on close.

## Troubleshooting

- "No API key found" — Make sure you have set the environment variable or set the key in-app.
- Key validation fails — Ensure the key starts with `sk-` and is active in your OpenAI account.
- Tkinter errors on Linux — install system package like `sudo apt-get install python3-tk`.
- Network/timeout errors — check connectivity and that your OpenAI account has access to the requested models.
- If `.env` saving fails, the app will still work for the current session; you can manually add the `OPENAI_API_KEY` to a `.env` file.

## Packaging into a standalone executable (optional)
You can use tools like PyInstaller to create a single executable:
1. pip install pyinstaller
2. pyinstaller --onefile --windowed chat_client.py
3. The executable will be in `dist/`

## Development / Contribution
Contributions, bug reports, and feature requests are welcome. Please open an issue or submit a pull request. Consider:
- Improving error handling
- Adding settings persistence beyond `.env` (e.g., config file)
- Adding message editing
- Adding token usage tracking and limits

## License
MIT License — see LICENSE file. Feel free to reuse and modify.
