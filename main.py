import os
import tempfile
import wave
import pyaudio
import keyboard
import pyautogui
import pyperclip
from groq import Groq

# Set up Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# заранее надо біло установить ключ в переменные окружения через консоль, например:
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

    # show_pressed_keys()  # Start showing pressed keys in the terminal

    print("Нажимаем и держим кнопку ESC для старта записи аудио...")
    frames = []

    keyboard.wait("esc")  # Wait for ESC button to be pressed
    print("Запись... (Отпустите ESC для остановки)")

    while keyboard.is_pressed("esc"):
        data = stream.read(chunk)
        frames.append(data)

    print("Запись завершена.")
    stream.stop_stream()
    stream.close()
    p.terminate()

    return frames, sample_rate

def show_pressed_keys():
    """
    Показывает имена нажатых клавиш в терминале в реальном времени.
    Для выхода нажмите ESC.
    """
    print("Нажимайте клавиши (ESC для выхода):")
    while True:
        event = keyboard.read_event()
        if event.event_type == keyboard.KEY_DOWN:
            print(f"Key pressed: {event.name}")
            if event.name == "esc":
                print("Выход из режима отображения клавиш.")
                break

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
    while True:
        # Record audio
        frames, sample_rate = record_audio()

        # Save audio to temporary file
        temp_audio_file = save_audio(frames, sample_rate)

        # Transcribe audio
        print("Транскрибируем аудио...")
        transcription = transcribe_audio(temp_audio_file)

        # Copy transcription to clipboard
        if transcription:
            print("\Транскрипция:")
            print(transcription)
            print("Копируем транскрипцию в буфер обмена...")
            copy_transcription_to_clipboard(transcription)
            print("Транскрипция скопирована в буфер обмена и вставлена в приложение.")
        else:
            print("Транскрибация не удалась.")

        # Clean up temporary file
        os.unlink(temp_audio_file)

        print("\nГотово для следующей записи. Нажмите ESC для начала.")


if __name__ == "__main__":
    main()
