import datetime
import pytz

# Таймзона Киева
KIEV_TZ = pytz.timezone("Europe/Kiev")


def now() -> datetime.datetime:
    """
    Возвращает текущее время в таймзоне Киева.
    """
    return datetime.datetime.now(KIEV_TZ)


def naive_now() -> datetime.datetime:
    """
    Возвращает текущее время в таймзоне Киева, но без информации о таймзоне (naive datetime).
    Используется для сравнения с naive datetime из базы данных.
    """
    return now().replace(tzinfo=None)


def parse_datetime_naive(datetime_str: str, format_str: str = "%Y-%m-%d %H:%M") -> datetime.datetime:
    """
    Парсит строку с датой и временем, интерпретируя её как время в таймзоне Киева,
    но возвращает naive datetime (без таймзоны) для совместимости с базой данных.
    
    Args:
        datetime_str: Строка с датой и временем
        format_str: Формат строки (по умолчанию "%Y-%m-%d %H:%M")
    
    Returns:
        Naive datetime объект (без таймзоны)
    """
    # Парсим как naive datetime
    dt = datetime.datetime.strptime(datetime_str, format_str)
    # Предполагаем, что введенное время - это время в таймзоне Киева
    # Используем localize для pytz
    dt_kiev = KIEV_TZ.localize(dt)
    # Возвращаем naive версию для сохранения в БД
    return dt_kiev.replace(tzinfo=None)

