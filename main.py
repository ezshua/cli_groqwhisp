import os
import ctypes
import tempfile
import threading
import wave
import pyaudio
import pyautogui
import pyperclip
from groq import Groq

# Активация поддержки ANSI-последовательностей в консоли Windows
os.system('')

# =============================================================================
# НАСТРОЙКИ
# =============================================================================

# Режим управления: "hotkey" — комбинация клавиш, "media" — мультимедиа клавиши
INPUT_MODE = "media"  # "hotkey" | "media"

# --- Режим hotkey ---
# Комбинация клавиш для записи (удерживать)
RECORD_KEY_COMBINATION = "ctrl+alt+r"

# --- Режим media: назначение мультимедиа клавиш по функциям ---
# VK-коды: 0xB3=Play/Pause, 0xB0=Next Track, 0xB1=Prev Track, 0xB2=Stop
# https://learn.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes
MEDIA_KEY_RECORD       = 0xB3  # Удерживать для записи, отпустить — отправить
MEDIA_KEY_MODEL_SWITCH = 0xB0  # Переключение модели Whisper (Next Track)
MEDIA_KEY_LANG_SWITCH  = 0xB1  # Переключение языка (Prev Track)
MEDIA_KEY_EXIT         = 0xB2  # Завершение программы (Stop)

# --- Языки для переключения ---
# Коды языков Whisper: "ru", "en", "de", "fr", "uk" и др.
# https://platform.openai.com/docs/guides/speech-to-text/supported-languages
LANGUAGES = ["ru", "en"]

# --- Модели Whisper для переключения ---
MODELS = ["whisper-large-v3-turbo", "whisper-large-v3"]

# =============================================================================
# КОНСТАНТЫ ОФОРМЛЕНИЯ
# =============================================================================

RESET  = "\033[0m"
BOLD   = "\033[1m"
ITALIC = "\033[3m"

RED    = "\033[91m"
GREEN  = "\033[92m"
BLUE   = "\033[94m"
YELLOW = "\033[93m"

GRAY      = "\033[37m"
CYAN      = "\033[96m"
DGRAY     = "\033[90m"

# =============================================================================
# GROQ CLIENT
# =============================================================================

# Установить ключ заранее через консоль:
# setx GROQ_API_KEY "your-api-key-here"
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# =============================================================================
# СОСТОЯНИЕ
# =============================================================================

recording   = False
lang_index  = 0
model_index = 0
user32      = ctypes.windll.user32

# pyautogui.PAUSE = 0.5
# pyautogui.FAILSAFE = True

ALL_MEDIA_KEYS = {
    MEDIA_KEY_RECORD:       "Record",
    MEDIA_KEY_MODEL_SWITCH: "Model Switch",
    MEDIA_KEY_LANG_SWITCH:  "Lang Switch",
    MEDIA_KEY_EXIT:         "Exit",
}
prev_state = {vk: False for vk in ALL_MEDIA_KEYS}

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def get_language():
    return LANGUAGES[lang_index]

def get_model():
    return MODELS[model_index]

def print_status():
    """Печатает текущий язык и модель."""
    print(
        f"{ITALIC}Язык: {BOLD}{get_language().upper()}{RESET}  "
        f"{ITALIC}Модель: {BOLD}{get_model()}{RESET}"
    )

# =============================================================================
# ОБРАБОТЧИКИ МЕДИА-КЛАВИШ
# =============================================================================

def on_key_down(vk):
    global recording
    if vk == MEDIA_KEY_RECORD:
        if not recording:
            recording = True
            print(f"{RED}{BOLD}Запись... (Отпустите клавишу для остановки){RESET}")

def on_key_up(vk):
    global recording, lang_index, model_index
    if vk == MEDIA_KEY_RECORD:
        if recording:
            recording = False  # сигнал record_audio завершить цикл
    elif vk == MEDIA_KEY_LANG_SWITCH:
        lang_index = (lang_index + 1) % len(LANGUAGES)
        print(f"{YELLOW}Язык переключён на: {BOLD}{get_language().upper()}{RESET}")
    elif vk == MEDIA_KEY_MODEL_SWITCH:
        model_index = (model_index + 1) % len(MODELS)
        print(f"{YELLOW}Модель переключена на: {BOLD}{get_model()}{RESET}")
    elif vk == MEDIA_KEY_EXIT:
        print(f"\n{RED}{BOLD}Завершение программы...{RESET}")
        os._exit(0)

def poll_media_keys():
    """Опрос состояния медиа-клавиш, вызов обработчиков на фронтах."""
    for vk in ALL_MEDIA_KEYS:
        pressed = bool(user32.GetAsyncKeyState(vk) & 0x8000)
        if pressed and not prev_state[vk]:
            on_key_down(vk)
        elif not pressed and prev_state[vk]:
            on_key_up(vk)
        prev_state[vk] = pressed

# =============================================================================
# АУДИО
# =============================================================================

def _poll_keys_thread():
    """Фоновый поток опроса медиа-клавиш во время записи."""
    import time
    while recording:
        poll_media_keys()
        time.sleep(0.02)


def record_audio(sample_rate=16000, channels=1, chunk=1024):
    """
    Записывает аудио с микрофона.
    Режим media:  пока recording=True (сбрасывается в on_key_up).
                  Опрос клавиш идёт в отдельном потоке.
    Режим hotkey: пока удерживается RECORD_KEY_COMBINATION.
    """
    global recording

    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=channels,
        rate=sample_rate,
        input=True,
        frames_per_buffer=chunk,
    )

    frames = []

    if INPUT_MODE == "media":
        poller = threading.Thread(target=_poll_keys_thread, daemon=True)
        poller.start()

        while recording:
            data = stream.read(chunk)
            frames.append(data)

        poller.join(timeout=0.1)
    else:
        import keyboard
        while keyboard.is_pressed(RECORD_KEY_COMBINATION):
            data = stream.read(chunk)
            frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()
    print(f"{ITALIC}{YELLOW}Запись завершена.{RESET}")
    return frames, sample_rate


def save_audio(frames, sample_rate):
    """Сохраняет записанное аудио во временный WAV-файл."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        wf = wave.open(temp_audio.name, "wb")
        wf.setnchannels(1)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(frames))
        wf.close()
        return temp_audio.name


def translate_audio(audio_file_path):
    """Переводит аудио через Groq Whisper."""
    if (lang_index == 1 and model_index == 1):  
        # en + "whisper-large-v3" = перевод, а не транскрипция
        try:
            with open(audio_file_path, "rb") as file:
                translations = client.audio.translations.create(
                    file=(os.path.basename(audio_file_path), file.read()),
                    model=get_model(),
                    prompt="The audio is a common discussions with elements of technical terms and science language. Translate this to English.",
                    # prompt="""The audio is by a programmer discussing programming issues, 
                    #           the programmer mostly uses python and might mention python 
                    #           libraries or reference code in his speech.""",
                    response_format="text",
                )
            return translations
        except Exception as e:
            print(f"{ITALIC}{RED}Ошибка перевода: {str(e)}{RESET}")
            return None
        
def transcribe_audio(audio_file_path):
    # Иначе — обычная транскрипция, со случайным переводом иногда при en + "whisper-large-v3-turbo", так как модель может сама решить, что нужно перевести для лучшего результата
    try:
        with open(audio_file_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(audio_file_path), file.read()),
                model=get_model(),
                prompt="The audio is a common discussions with elements of technical terms and science language.",
                # prompt="""The audio is by a programmer discussing programming issues, 
                #           the programmer mostly uses python and might mention python 
                #           libraries or reference code in his speech.""",
                response_format="text",
                language=get_language() if INPUT_MODE == "media" else "ru",
            )
        return transcription
    except Exception as e:
        print(f"{ITALIC}{RED}Ошибка транскрибации: {str(e)}{RESET}")
        return None


def copy_transcription_to_clipboard(text):
    """Копирует текст в буфер обмена и вставляет в активное окно."""
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "v")

# =============================================================================
# ОСНОВНОЙ ЦИКЛ
# =============================================================================

def main():
    import time

    if INPUT_MODE == "media":
        print(f"{BOLD}Управление:{RESET}")
        print(f"  {BOLD} ⏯   Play/Pause{RESET}  — удерживать для записи, отпустить — отправить")
        print(f"  {BOLD} ⏮   Prev Track {RESET}  — переключить язык       {YELLOW}(сейчас: {get_language().upper()}){RESET}")
        print(f"  {BOLD} ⏭   Next Track {RESET}  — переключить модель     {YELLOW}(сейчас: {get_model()}){RESET}")
        print(f"  {BOLD} ⏹   Stop       {RESET}  — завершить программу")
        print()
    else:
        import keyboard
        print(f"{ITALIC}Нажмите и удерживайте {BOLD}{RECORD_KEY_COMBINATION.upper()}{RESET}{ITALIC} для записи.{RESET}\n")

    while True:

        if INPUT_MODE == "media":
            print(f"{ITALIC}Готов.  ", end="")
            print_status()
            while not recording:
                poll_media_keys()
                time.sleep(0.02)
        else:
            import keyboard
            print(f"\n{ITALIC}Готово для следующей записи. Нажмите и удерживайте "
                  f"{BOLD}{RECORD_KEY_COMBINATION.upper()}{RESET}{ITALIC} для начала.{RESET}")
            keyboard.wait(RECORD_KEY_COMBINATION)
            print(f"\n{RED}{BOLD}Запись... (Отпустите {RECORD_KEY_COMBINATION.upper()} для остановки){RESET}")

        # Запись
        frames, sample_rate = record_audio()

        # Сохранение
        temp_audio_file = save_audio(frames, sample_rate)

        # Транскрипция
        if lang_index == 1 and model_index == 1:
            print(f"{ITALIC}{CYAN}Переводим аудио ({get_model()}, {get_language().upper()})...{RESET}")
            result = translate_audio(temp_audio_file)
        else:
            print(f"{ITALIC}{CYAN}Транскрибируем аудио ({get_model()}, {get_language().upper()})...{RESET}")
            result = transcribe_audio(temp_audio_file)

        # Результат
        if result:
            if lang_index == 1 and model_index == 1:
                print(f"\n{BLUE}{ITALIC}Перевод:{RESET}")
            else:
                print(f"\n{BLUE}{ITALIC}Транскрипция:{RESET}")
            print(f"\t{GREEN}{BOLD}{result}{RESET}")
            # print(f"\n{ITALIC}Копируем в буфер обмена...{RESET}")
            copy_transcription_to_clipboard(result)
            if lang_index == 1 and model_index == 1:
                print(f"\n{ITALIC}{DGRAY}Перевод скопирован и вставлен{RESET}")
            else:
                print(f"\n{ITALIC}{DGRAY}Транскрипция скопирована и вставлена{RESET}")
        else:
            print(f"{RED}Обработка не удалась.{RESET}")

        # Удаление временного файла
        os.unlink(temp_audio_file)


if __name__ == "__main__":
    main()