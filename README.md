# Groq Whisperer: Voice-to-Text CLI Transcription Tool

**Groq Whisperer** is a Python-based application that allows users to record audio and transcribe it to text using Groq's Whisper implementation. The transcribed text is automatically copied to the clipboard for easy pasting into other applications.

## Features

- Hybrid input mode (single mode): hotkey + multimedia keys work simultaneously
- Record audio by holding down **F9** (default, configurable in `main.py` or **Ctrl+Alt+V** key combination, for example)
- Record audio by holding down **Play/Pause** multimedia key
- Switch transcription language with **Prev Track** multimedia key
- Switch Whisper model with **Next Track** multimedia key
- Exit application with **Stop** multimedia key
- Transcribe recorded audio to text using Groq's API
- Automatic translation mode for **EN + whisper-large-v3** combination
- Automatically copy transcription to clipboard
- Automatically paste transcription into active window
- Continuous operation for multiple recordings

## Prerequisites

- Python 3.7 or higher
- A Groq API key (`gsk_...`)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/ezshua/cli_groqwhisp.git
   cd cli_groqwhisp
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS and Linux:
     ```
     source venv/bin/activate
     ```

4. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

5. Set up your Groq API key (recommended: environment variable):
   - On Windows:
     ```
     setx GROQ_API_KEY "your-api-key-here"
     ```
   - On macOS and Linux:
     ```
     export GROQ_API_KEY="your-api-key-here"
     ```
   You can also pass the key directly at launch with `--groq-api-key`.

## First launch on Windows (automated)

You can do initial setup and first run with a single command file:

```
first_start_setup.bat
```

What it does:
- creates `venv` (tries Python 3.11 first, then default `py`)
- upgrades `pip`
- installs packages from `requirements.txt`
- checks `GROQ_API_KEY` in current session and user environment
- asks for API key once and saves it via `setx` if missing
- starts the app in background

## Build binary for PCs without Python (Windows)

To build a standalone `.exe`:

```
build_exe.bat
```

Output file:

```
dist\main.exe
```

You can copy `dist\main.exe` to another Windows PC and run it without installing Python.

### How to rebuild in the future

When you change `main.py` or dependencies, rebuild with:

1. `first_start_setup.bat` (if environment is missing or outdated)
2. `build_exe.bat`
3. test `dist\main.exe` on your machine
4. distribute the new `dist\main.exe`

## Usage

1. Run the script from console:
   ```
   python main.py
   ```
   or use command files:
   ```
   first_start_setup.bat
   startw.bat
   ```
   - `first_start_setup.bat` for first install + launch
   - `startw.bat` for regular launch after setup

2. Optional command-line arguments:
   - Show help message:
     ```
     python main.py --help
     ```
   - Show available input devices:
     ```
     python main.py --list-audio
     ```
   - Select a specific input device index:
     ```
     python main.py --set-audio 2
     ```
   - Save recorded WAV files to a directory:
     ```
     python main.py --save-record-dir "C:\temp\groqwhisp_records"
     ```
   - Pass Groq API key directly in CLI (has priority over `GROQ_API_KEY`):
     ```
     python main.py --groq-api-key "gsk_..."
     ```
   - Combine options:
     ```
     python main.py --set-audio 2 --save-record-dir "C:\temp\groqwhisp_records" --groq-api-key "gsk_..."
     ```

### Groq API key behavior

- Key format must start with `gsk_`.
- Key source priority: `--groq-api-key` first, then `GROQ_API_KEY`.
- On startup, app prints masked key preview in this format: `gsk_abc...xyz`.
- If key is missing or invalid, app shows an extended setup hint and exits.

3. Control options in the running app:
   - Press and hold **F9** to start recording (release to stop and send)
   - Or use **Play/Pause** multimedia key for the same action
   - Use **Prev Track** to switch language (`LANGUAGES` in `main.py`)
   - Use **Next Track** to switch model (`MODELS` in `main.py`)
   - Use **Stop** to exit the application
4. After processing, the result text is copied to clipboard and inserted into the active window.
5. Repeat recording as needed (the app runs continuously).

## Dependencies

The project relies on the following main libraries:

- `pyaudio`: For audio recording
- `ctypes` (Windows API): For low-level key state polling via `GetAsyncKeyState`
- `pyautogui` and `pyperclip`: For clipboard operations
- `groq`: For interacting with the Groq API

For a complete list of dependencies, see the `requirements.txt` file.

## Notes

- Make sure your microphone is properly configured and working before running the script.
- The transcription quality may vary depending on the audio quality and background noise.
- Ensure you have a stable internet connection for the transcription process.

## License

[MIT License](LICENSE)
