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
- A Groq API key (set as an environment variable)

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

5. Set up your Groq API key as an environment variable:
   - On Windows:
     ```
     setx GROQ_API_KEY "your-api-key-here"
     ```
   - On macOS and Linux:
     ```
     export GROQ_API_KEY="your-api-key-here"
     ```

## Usage

1. Run the script from console:
   ```
   python main.py
   ```
   or 
   создайте ярлык для омандного файла 
   ```
   startw.bat
   ```
   и запускайте его, а по окончанию работы закрывайте консольное окно

2. Control options in the running app:
   - Press and hold **F9** to start recording (release to stop and send)
   - Or use **Play/Pause** multimedia key for the same action
   - Use **Prev Track** to switch language (`LANGUAGES` in `main.py`)
   - Use **Next Track** to switch model (`MODELS` in `main.py`)
   - Use **Stop** to exit the application
3. After processing, the result text is copied to clipboard and inserted into the active window.
4. Repeat recording as needed (the app runs continuously).

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
