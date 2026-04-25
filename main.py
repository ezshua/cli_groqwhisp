import os
import tempfile
import wave
import pyaudio
import keyboard
import pyautogui
import pyperclip
from groq import Groq
from keyb import show_pressed_keys, media_pressed_keys

# Активация поддержки ANSI-последовательностей в консоли Windows
os.system('')

# Константы для оформления текста
RESET = "\033[0m" # Сброс всех атрибутов
BOLD = "\033[1m"
ITALIC = "\033[3m"
NORMAL = "\033[22m"  # Отмена жирного шрифта

RED = "\033[91m"
GREEN = "\033[92m"
BLUE = "\033[94m"

# Комбинация клавиш для начала/остановки записи
RECORD_KEY_COMBINATION = "ctrl+alt+r" # Вы можете изменить эту комбинацию на любую другую, например "shift+f10"

# Set up Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# заранее надо было установить ключ в переменные окружения через консоль, например:
# setx GROQ_API_KEY "your-api-key-here"

def record_audio(sample_rate=16000, channels=1, chunk=1024):
    """
    Record audio from the microphone while the PAUSE button is held down.
    """
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=channels,
        rate=sample_rate,
        input=True,
        frames_per_buffer=chunk,
    )

    # print("Нажимаем и держим кнопку ESC для старта записи аудио...")
    frames = []
    
    keyboard.wait(RECORD_KEY_COMBINATION)  # Ждем нажатия комбинации клавиш
    print(f"{RED}{BOLD}Запись... (Отпустите {RECORD_KEY_COMBINATION.upper()} для остановки){RESET}")

    while keyboard.is_pressed(RECORD_KEY_COMBINATION):
        data = stream.read(chunk)
        frames.append(data)

    print("Запись завершена.")
    stream.stop_stream()
    stream.close()
    p.terminate()

    return frames, sample_rate

def save_audio(frames, sample_rate):
    """
    Save recorded audio to a temporary WAV file.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        wf = wave.open(temp_audio.name, "wb")
        wf.setnchannels(1)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(frames))
        wf.close()
        return temp_audio.name


def transcribe_audio(audio_file_path):
    """
    Transcribe audio using Groq's Whisper implementation.
    """
    try:
        with open(audio_file_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(audio_file_path), file.read()),
                model="whisper-large-v3-turbo",
                prompt="""The audio is by a programmer discussing programming issues, the programmer mostly uses python and might mention python libraries or reference code in his speech.""",
                response_format="text",
                # language="en",
            )
        return transcription  # This is now directly the transcription text
    except Exception as e:
        print(f"Ашипка транскрибации аудио: {str(e)}")
        return None


def copy_transcription_to_clipboard(text):
    """
    Copy the transcribed text to clipboard using pyperclip.
    """
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "v")


def main():
      
    # media_pressed_keys()  # Start showing pressed keys in the terminal
    
    while True:

        print(f"\n{ITALIC}Готово для следующей записи. Нажмите и удерживайте {RECORD_KEY_COMBINATION.upper()} для начала.{RESET}")
        # Record audio
        frames, sample_rate = record_audio()

        # Save audio to temporary file
        temp_audio_file = save_audio(frames, sample_rate)

        # Transcribe audio
        print(f"{ITALIC}Транскрибируем аудио...{RESET}")
        transcription = transcribe_audio(temp_audio_file)

        # Copy transcription to clipboard
        if transcription:
            print(f"\n{BLUE}{ITALIC}Транскрипция:{RESET}")
            print(f"\t{GREEN}{BOLD}{transcription}{RESET}")
            print(f"\n{ITALIC}Копируем транскрипцию в буфер обмена...{RESET}")
            copy_transcription_to_clipboard(transcription)
            print(f"{BOLD}Транскрипция скопирована в буфер обмена и вставлена в приложение.{RESET}")
        else:
            print(f"{RED}Транскрибация не удалась.{RESET}")

        # Clean up temporary file
        os.unlink(temp_audio_file)


if __name__ == "__main__":
    main()
