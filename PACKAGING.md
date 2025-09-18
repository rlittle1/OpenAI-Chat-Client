Basic steps to create a standalone executable using PyInstaller:

Prep
- Create and activate a virtual environment:
  ```
  python -m venv venv
  ```
  # Windows
  ```
  venv\Scripts\activate
  ```
  # macOS / Linux
  ```
  source venv/bin/activate
  ```

- Install dependencies:
  ```
  pip install -r requirements.txt
  pip install openai  # ensure installed in the venv
  ```

- Make sure your script is named e.g. chat_client.py and runs properly with:
  ```
  python chat_client.py
  ```

Common PyInstaller commands
- One-file, windowed (no console) build for desktop app:
  ```
  pyinstaller --onefile --windowed chat_client.py
  ```

- If your app uses data files (icons, templates), include them with --add-data:
  ```
  pyinstaller --onefile --windowed --add-data "path/to/data:target_folder" chat_client.py
  ```
  Note: on Windows use semicolon separators; on macOS/linux use colon. Example:
  ```
  --add-data "assets/icon.ico;assets"
  ```

- After running, distributable binary will be in the dist/ folder.

Platform notes
- Windows:
  - Use a Windows machine or cross-compile using a Windows CI runner.
  - You can add an icon: --icon path/to/icon.ico
  - For signing executables, use signtool or a third-party provider if you plan to distribute widely.

- macOS:
  - Build on macOS.
  - Gatekeeper notarization and code-signing may be required for distribution outside the App Store.

Testing and distribution
- Test the binary on fresh machines/VMs when possible.
- Do not embed your API key in the binary. Use environment variables or prompt users to set keys.
- Provide a small README explaining how to set OPENAI_API_KEY before running the binary.

Troubleshooting
- Missing tkinter on Linux: install system package (Ubuntu/Debian):
  sudo apt-get install python3-tk
- If PyInstaller misses modules, read the PyInstaller warnings and add hidden imports:
  pyinstaller --hidden-import some_module ...
