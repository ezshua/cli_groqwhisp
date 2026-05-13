import os
import sys
import argparse
import ctypes
import shutil
import struct
import tempfile
import threading
from datetime import datetime
from pathlib import Path
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

# Единый режим управления: hotkey + мультимедиа клавиши одновременно
POLL_INTERVAL_SEC = 0.005  # 5ms: быстрый отклик на отпускание

# --- Режим hotkey ---
# Комбинация клавиш для записи (удерживать)
RECORD_KEY_COMBINATION = "f9"

# --- Режим media: назначение мультимедиа клавиш по функциям ---
# VK-коды: 0xB3=Play/Pause, 0xB0=Next Track, 0xB1=Prev Track, 0xB2=Stop
# https://learn.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes
MEDIA_KEY_RECORD       = 0xB3  # Удерживать для записи, отпустить — отправить
MEDIA_KEY_MODEL_SWITCH = 0xB0  # Переключение модели Whisper (Next Track)
MEDIA_KEY_LANG_SWITCH  = 0xB1  # Переключение языка (Prev Track)
MEDIA_KEY_EXIT         = 0xB2  # Завершение программы (Stop)

# --- Языки для переключения ---
# Коды языков Whisper: "ru", "en"
# https://platform.openai.com/docs/guides/speech-to-text/supported-languages
LANGUAGES = ["ru", "en"]

# --- Модели Whisper для переключения ---
MODELS = ["whisper-large-v3-turbo", "whisper-large-v3"]

# --- Отладка: сохранять WAV в директорию ---
# Используется аргумент командной строки: --save-record-dir PATH
RECORDINGS_DEBUG_SUBDIR = "record_debug"

# --- Ввод звука (PyAudio): None = устройство по умолчанию Windows / хоста ---
# Индекс из списка можно задать параметром запуска: --set-audio N
AUDIO_INPUT_DEVICE_INDEX = None
# Пик амплитуды int16 ниже этого — считаем запись «тишиной» (настройки / не тот микрофон).
SILENCE_PEAK_THRESHOLD = 64

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
IS_WINDOWS  = sys.platform.startswith("win")
user32      = ctypes.windll.user32 if IS_WINDOWS else None
input_actions = {}
action_prev_state = {}
RECORD_ACTIONS = {"record_hotkey", "record_media"}
save_recordings_debug = False
# Переопределяет директорию для сохранения WAV (если задана через CLI)
recordings_debug_out_dir_override = None

pyautogui.PAUSE = 0.3       # глюк со вставкой - включать и откючать в произвольном порядке если не работает автовставка
pyautogui.FAILSAFE = False # глюк со вставкой - включать и откючать в произвольном порядке если не работает автовставка

VK_ALIASES = {
    "ctrl": [0xA2, 0xA3],    # LCTRL, RCTRL
    "alt": [0xA4, 0xA5],     # LALT, RALT
    "shift": [0xA0, 0xA1],   # LSHIFT, RSHIFT
    "win": [0x5B, 0x5C],     # LWIN, RWIN
    "esc": [0x1B],
    "enter": [0x0D],
    "space": [0x20],
    "tab": [0x09],
}

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
# ОБРАБОТЧИКИ ВВОДА
# =============================================================================

def _token_to_vk_options(token):
    token = token.strip().lower()
    if token in VK_ALIASES:
        return VK_ALIASES[token]
    if token.startswith("f") and token[1:].isdigit():
        fn_num = int(token[1:])
        if 1 <= fn_num <= 24:
            return [0x6F + fn_num]  # F1..F24 -> 0x70..0x87
    if len(token) == 1 and token.isalnum():
        return [ord(token.upper())]
    raise ValueError(f"Неподдерживаемый токен в RECORD_KEY_COMBINATION: {token}")


def _parse_hotkey_combination(combination):
    parts = [p.strip() for p in combination.split("+") if p.strip()]
    if not parts:
        raise ValueError("RECORD_KEY_COMBINATION не может быть пустой.")
    return [_token_to_vk_options(part) for part in parts]


def _is_any_vk_pressed(vk_options):
    if not IS_WINDOWS or user32 is None:
        return False
    return any(bool(user32.GetAsyncKeyState(vk) & 0x8000) for vk in vk_options)


def _is_action_pressed(binding):
    if binding["type"] == "vk":
        return _is_any_vk_pressed([binding["vk"]])
    if binding["type"] == "combo":
        if not IS_WINDOWS:
            try:
                import keyboard
                return keyboard.is_pressed(binding["combo_str"])
            except Exception:
                return False
        return all(_is_any_vk_pressed(vk_options) for vk_options in binding["parts"])
    return False


def build_input_actions():
    actions = {
        "record_hotkey": {"type": "combo", "parts": _parse_hotkey_combination(RECORD_KEY_COMBINATION)},
        "record_media": {"type": "vk", "vk": MEDIA_KEY_RECORD},
        "model_switch": {"type": "vk", "vk": MEDIA_KEY_MODEL_SWITCH},
        "lang_switch": {"type": "vk", "vk": MEDIA_KEY_LANG_SWITCH},
        "exit": {"type": "vk", "vk": MEDIA_KEY_EXIT},
    }
    actions["record_hotkey"]["combo_str"] = RECORD_KEY_COMBINATION
    if not IS_WINDOWS:
        # На не-Windows WinAPI-механизм media-клавиш недоступен.
        for action_name in ("record_media", "model_switch", "lang_switch", "exit"):
            actions.pop(action_name, None)
    return actions


def init_input_actions():
    global input_actions, action_prev_state
    input_actions = build_input_actions()
    action_prev_state = {action_name: False for action_name in input_actions}


def on_action_down(action_name):
    global recording
    if action_name in RECORD_ACTIONS and not recording:
        recording = True
        print(f"{RED}{BOLD}Запись... (Отпустите клавишу для остановки){RESET}")


def _is_any_record_binding_pressed():
    return any(_is_action_pressed(input_actions[action]) for action in RECORD_ACTIONS)


def on_action_up(action_name):
    global recording, lang_index, model_index
    if action_name in RECORD_ACTIONS:
        if recording and not _is_any_record_binding_pressed():
            recording = False  # сигнал record_audio завершить цикл
    elif action_name == "lang_switch":
        lang_index = (lang_index + 1) % len(LANGUAGES)
        print(f"{YELLOW}Язык переключён на: {BOLD}{get_language().upper()}{RESET}")
    elif action_name == "model_switch":
        model_index = (model_index + 1) % len(MODELS)
        print(f"{YELLOW}Модель переключена на: {BOLD}{get_model()}{RESET}")
    elif action_name == "exit":
        print(f"\n{RED}{BOLD}Завершение программы...{RESET}")
        os._exit(0)


def poll_input_actions():
    """Единый опрос состояния действий, вызов обработчиков на фронтах."""
    for action_name, binding in input_actions.items():
        pressed = _is_action_pressed(binding)
        if pressed and not action_prev_state[action_name]:
            on_action_down(action_name)
        elif not pressed and action_prev_state[action_name]:
            on_action_up(action_name)
        action_prev_state[action_name] = pressed

# =============================================================================
# АУДИО
# =============================================================================

def _resolved_input_device_index():
    return AUDIO_INPUT_DEVICE_INDEX


def report_audio_inputs(full_list=False):
    """Показывает вход по умолчанию и при full_list — все устройства ввода PyAudio."""
    p = pyaudio.PyAudio()
    try:
        try:
            default = p.get_default_input_device_info()
        except OSError:
            default = None
            print(f"{RED}Нет устройства ввода по умолчанию (микрофон не выбран или запрещён).{RESET}")

        chosen = _resolved_input_device_index()
        if full_list:
            print(f"{BOLD}Устройства ввода (индекс -> имя):{RESET}")
            found_any = False
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if int(info.get("maxInputChannels", 0)) < 1:
                    continue
                found_any = True
                mark = ""
                if default and i == default["index"]:
                    mark = f" {GREEN}<- default{RESET}"
                sr = int(info.get("defaultSampleRate", 0))
                name = str(info.get("name", ""))[:72]
                hi = f"{CYAN}{i:3d}{RESET}"
                print(f"  {hi}  {name}  ({sr} Hz){mark}")
            if not found_any:
                print(f"  {YELLOW}(нет устройств с maxInputChannels > 0){RESET}")
            print()

        if default:
            print(
                f"{ITALIC}Вход по умолчанию: [{default['index']}] {default['name']}{RESET}"
            )
        if chosen is not None:
            try:
                inf = p.get_device_info_by_index(chosen)
                print(
                    f"{YELLOW}Запись с устройства [{chosen}]: {inf['name']}{RESET}"
                )
            except OSError:
                print(
                    f"{RED}Параметр --set-audio={chosen} — устройство не найдено.{RESET}"
                )
        elif default:
            print(
                f"{ITALIC}{DGRAY}Подсказка: при тишине выберите другой индекс "
                f"(--set-audio N), или посмотрите список: --list-audio{RESET}"
            )
    finally:
        p.terminate()


def _frames_int16_peak_abs(frames):
    """Максимум |sample| для буферов int16 little-endian."""
    if not frames:
        return 0
    raw = b"".join(frames)
    n = len(raw) // 2
    if n == 0:
        return 0
    fmt = f"<{n}h"
    if len(raw) < n * 2:
        return 0
    samples = struct.unpack(fmt, raw[: n * 2])
    return max((abs(s) for s in samples), default=0)


def _text_is_only_thank_you(text):
    """Whisper часто выдаёт «Thank you.» на почти пустом аудио — триггер для проверки уровня."""
    if not isinstance(text, str):
        return False
    t = " ".join(text.strip().split()).lower().rstrip(".")
    return t == "thank you"


def report_record_level(frames):
    """Предупреждает при почти нулевом сигнале; при отладке печатает пик."""
    peak = _frames_int16_peak_abs(frames)
    if peak < SILENCE_PEAK_THRESHOLD:
        print(
            f"{RED}{BOLD}Запись похожа на тишину{RESET} "
            f"{RED}(пик амплитуды {peak}, порог {SILENCE_PEAK_THRESHOLD}).{RESET}"
        )
        print(
            f"{ITALIC}Система: Параметры -> Конфиденциальность -> Микрофон — доступ для приложений; "
            f"Параметры -> Система -> Звук -> нужный микрофон — проверка и громкость ввода.{RESET}"
        )
        print(
            f"{ITALIC}Программа: задайте другой индекс устройства "
            f"(--set-audio N), см. список: python main.py --list-audio{RESET}"
        )
    elif _recordings_debug_enabled():
        print(f"{ITALIC}{DGRAY}Пик сигнала (int16): {peak} / 32767{RESET}")
    return peak


def _poll_keys_thread():
    """Фоновый поток опроса действий во время записи."""
    import time
    while recording:
        poll_input_actions()
        time.sleep(POLL_INTERVAL_SEC)


def record_audio(sample_rate=16000, channels=1, chunk=256):
    """
    Записывает аудио с микрофона.
    Единый режим: запись идёт пока recording=True.
    recording переключается обработчиком фронтов on_action_down/on_action_up.
    """
    device_index = _resolved_input_device_index()
    p = pyaudio.PyAudio()
    open_kw = dict(
        format=pyaudio.paInt16,
        channels=channels,
        rate=sample_rate,
        input=True,
        frames_per_buffer=chunk,
    )
    if device_index is not None:
        open_kw["input_device_index"] = device_index
    try:
        stream = p.open(**open_kw)
    except OSError as e:
        p.terminate()
        print(
            f"{RED}Не удалось открыть микрофон (частота {sample_rate} Гц, "
            f"устройство {device_index!r}): {e}{RESET}"
        )
        print(
            f"{ITALIC}Попробуйте другой --set-audio или смените "
            f"микрофон по умолчанию в Windows.{RESET}"
        )
        raise

    frames = []
    poller = threading.Thread(target=_poll_keys_thread, daemon=True)
    poller.start()

    while recording:
        data = stream.read(chunk, exception_on_overflow=False)
        frames.append(data)

    poller.join(timeout=0.1)

    stream.stop_stream()
    stream.close()
    p.terminate()
    print(f"{ITALIC}{YELLOW}Запись завершена.{RESET}")
    return frames, sample_rate


def _recordings_debug_enabled():
    return save_recordings_debug


def save_debug_recording_copy(wav_path):
    """Копирует WAV в директорию для отладочного анализа."""
    if not _recordings_debug_enabled():
        return None
    app_dir = Path(__file__).resolve().parent
    out_dir = (
        Path(recordings_debug_out_dir_override).expanduser().resolve()
        if recordings_debug_out_dir_override
        else (app_dir / RECORDINGS_DEBUG_SUBDIR)
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    name = datetime.now().strftime("recording_%Y%m%d_%H%M%S_%f.wav")
    dest = out_dir / name
    shutil.copy2(wav_path, dest)
    print(f"{ITALIC}{DGRAY}Отладка: аудио сохранено: {dest}{RESET}")
    return dest


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
                language=get_language(),
            )
        return transcription
    except Exception as e:
        print(f"{ITALIC}{RED}Ошибка транскрибации: {str(e)}{RESET}")
        return None


def copy_transcription_to_clipboard(text):
    """Копирует текст в буфер обмена и вставляет в активное окно."""
    import time # глюк со вставкой - включать и откючать в произвольном порядке если не работает автовставка                  
    pyperclip.copy(text)
    time.sleep(0.3)  # Дать время окну восстановить фокус # глюк со вставкой - включать и откючать в произвольном порядке если не работает автовставка
    pyautogui.hotkey("ctrl", "v")

# =============================================================================
# ОСНОВНОЙ ЦИКЛ
# =============================================================================

def main():
    import time

    init_input_actions()

    report_audio_inputs(full_list=False)
    print()

    print(f"Установить ключ в переменную окружения заранее через консоль:")
    print(f"setx GROQ_API_KEY \"your-api-key-here\"\n")
    if _recordings_debug_enabled():
        dbg_path = (
            Path(recordings_debug_out_dir_override).expanduser().resolve()
            if recordings_debug_out_dir_override
            else (Path(__file__).resolve().parent / RECORDINGS_DEBUG_SUBDIR)
        )
        print(f"{ITALIC}{DGRAY}Сохранение записей для отладки: {dbg_path}{RESET}")
    print(f"{BOLD}Управление:{RESET}")
    print(f"  {BOLD}{RECORD_KEY_COMBINATION.upper()}{RESET} — удерживать для записи, отпустить — отправить")
    if IS_WINDOWS:
        print(f"  {BOLD} ⏯   Play/Pause{RESET}          — удерживать для записи, отпустить — отправить")
        print(f"  {BOLD} ⏮   Prev Track{RESET}          — переключить язык       {YELLOW}(сейчас: {get_language().upper()}){RESET}")
        print(f"  {BOLD} ⏭   Next Track{RESET}          — переключить модель     {YELLOW}(сейчас: {get_model()}){RESET}")
        print(f"  {BOLD} ⏹   Stop{RESET}                — завершить программу")
    else:
        print(f"{YELLOW}Media-клавиши отключены: WinAPI-опрос доступен только на Windows.{RESET}")
    print()

    while True:
        print(f"{ITALIC}Готов.  ", end="")
        print_status()
        while not recording:
            poll_input_actions()
            time.sleep(POLL_INTERVAL_SEC)

        # Запись
        try:
            frames, sample_rate = record_audio()
        except OSError:
            continue

        # Сохранение
        temp_audio_file = save_audio(frames, sample_rate)
        save_debug_recording_copy(temp_audio_file)

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
            if _text_is_only_thank_you(result):
                print(
                    f"\n{YELLOW}{ITALIC}Ответ только «Thank you» — проверка пика амплитуды записи:{RESET}"
                )
                report_record_level(frames)
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
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "-l",
        "--list-audio",
        action="store_true",
        help="Показать доступные устройства записи",
    )
    parser.add_argument(
        "-m",
        "--set-audio",
        dest="set_audio",
        type=int,
        default=None,
        metavar="N",
        help="Индекс устройства записи из списка --list-audio",
    )
    parser.add_argument(
        "-d",
        "--save-record-dir",
        dest="save_record_dir",
        default=None,
        metavar="PATH",
        help="Директория для сохранения WAV. Если указана, файлы будут сохраняться в эту директорию",
    )
    args = parser.parse_args()

    AUDIO_INPUT_DEVICE_INDEX = args.set_audio
    recordings_debug_out_dir_override = args.save_record_dir
    # Включаем сохранение только когда задана реальная директория.
    save_recordings_debug = recordings_debug_out_dir_override is not None
    if args.list_audio:
        report_audio_inputs(full_list=True)
        sys.exit(0)
    main()