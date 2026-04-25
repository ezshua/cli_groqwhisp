import time
from queue import Queue, Empty
import keyboard
import ctypes
import time

# Константы для оформления текста (дублируем для автономности модуля)
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
BLUE = "\033[94m"

# gemini edition
def show_pressed_keys():
    """
    Служебная функция для определения кодов клавиш и их комбинаций.
    Выводит результат в формате, который можно сразу использовать в RECORD_KEY_COMBINATION.
    Если удерживать комбинацию 3 секунды без изменений, выведет готовую строку для константы.
    """
    print(f"\n{BLUE}{BOLD}=== Режим глубокого анализа клавиш ==={RESET}")
    print(f"Если кнопка Play/Pause выдает 'g', ищите пометку [MEDIA: ...] в выводе.")
    print(f"Нажмите {RED}ESC{RESET} для выхода.\n")

    event_queue = Queue()
    # Регистрируем хук, который будет перехватывать все события клавиатуры
    hook = keyboard.hook(event_queue.put)

    # Список стандартных медиа-имен для проверки
    media_names = [
        'play/pause media', 'media play/pause', 'play/pause',
        'next track', 'previous track', 'stop media',
        'volume up', 'volume down', 'volume mute', 'mute',
        'browser back', 'browser forward', 'browser refresh', 'browser search'
    ]
    
    current_keys = {}  # Словарь для хранения зажатых в данный момент клавиш
    last_change_time = time.time()
    displayed_stable_combo = False

    try:
        while True:
            try:
                # Пытаемся получить событие из очереди с коротким таймаутом
                event = event_queue.get(timeout=0.1)
                
                if event.name == 'esc' and event.event_type == keyboard.KEY_DOWN:
                    print(f"\n{BLUE}Выход из режима захвата.{RESET}")
                    break

                # Обработка нажатия/отпускания
                if event.event_type == keyboard.KEY_DOWN:
                    if event.name in current_keys:
                        continue  # Игнорируем автоповтор нажатия
                    
                    current_keys[event.name] = True
                    last_change_time = time.time()
                    displayed_stable_combo = False
                    color, action = RED, "НАЖАТО "
                else:
                    if event.name not in current_keys:
                        continue  # Игнорируем отпускание, если нажатие не было зафиксировано
                    
                    current_keys.pop(event.name)
                    last_change_time = time.time()
                    displayed_stable_combo = False
                    color, action = GREEN, "ОТПУЩЕНО"

                # Глубокая проверка: ищем, не считает ли система это нажатие медийным
                active_media = []
                for m in media_names:
                    try:
                        if keyboard.is_pressed(m):
                            active_media.append(m)
                    except (ValueError, KeyError):
                        continue
                
                media_info = f" {BLUE}{BOLD}[СИСТЕМНОЕ ИМЯ: {','.join(active_media)}]{RESET}" if active_media else ""

                print(f"{color}[{action}] Имя: {event.name:10} Код: {event.scan_code:3}{media_info}{RESET}")
                
                # Если это нажатие и оно совпадает с G, но есть медиа-имя - это успех
                if event.event_type == keyboard.KEY_DOWN and active_media:
                    print(f"{GREEN}Найдено уникальное имя для RECORD_KEY_COMBINATION: \"{active_media[0]}\"{RESET}")

            except Empty:
                if current_keys and not displayed_stable_combo:
                    if time.time() - last_change_time > 3.0:
                        # Создаем комбинацию имен
                        name_combo = "+".join(current_keys.keys())
                        # И альтернативную комбинацию через скан-коды
                        scan_combo = "+".join([f"#{code}" for code in [keyboard.key_to_scan_codes(k)[0] if not k.startswith('#') else k[1:] for k in current_keys.keys()]])
                        
                        print(f"\n{BLUE}{BOLD}>>> СТАБИЛЬНАЯ КОМБИНАЦИЯ (3 сек):{RESET}")
                        print(f"{GREEN}{BOLD}Вариант 1 (имена): RECORD_KEY_COMBINATION = \"{name_combo}\"{RESET}")
                        print(f"{GREEN}{BOLD}Вариант 2 (коды):  RECORD_KEY_COMBINATION = \"{scan_combo}\"{RESET}\n")
                        displayed_stable_combo = True
    finally:
        keyboard.unhook(hook)

# claude edition
def media_pressed_keys():

    user32 = ctypes.windll.user32

    MEDIA_KEYS = {
        0xB3: "Play/Pause",
        0xB0: "Next Track",
        0xB1: "Prev Track",
        0xB2: "Stop",
    }

    prev_state = {vk: False for vk in MEDIA_KEYS}

    def on_key_down(vk, name):
        """Нажатие клавиши"""
        print(f"↓ {name} нажата")

    def on_key_up(vk, name):
        """Отпускание клавиши"""
        print(f"↑ {name} отпущена")

    print("Слушаем медиа-клавиши... (Ctrl+C для выхода)")

    while True:
        for vk, name in MEDIA_KEYS.items():
            pressed = bool(user32.GetAsyncKeyState(vk) & 0x8000)

            if pressed and not prev_state[vk]:
                on_key_down(vk, name)
            elif not pressed and prev_state[vk]:
                on_key_up(vk, name)

            prev_state[vk] = pressed

        time.sleep(0.02)  # 20мс — достаточно быстро, без задержки