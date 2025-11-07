from datetime import datetime, timedelta
import calendar

WORKING_HOURS = {
    'mon-thu': {'start': 18, 'end': 23},
    'fri': {'start': 17, 'end': 23},
    'sat': {'start': 14, 'end': 19}
}


def get_available_weeks():
    """Возвращает список доступных недель для бронирования (4 недели)"""
    today = datetime.now().date()
    weeks = []

    for week_offset in range(0, 4):  # 4 недели вперед
        start_date, end_date = get_week_range(week_offset)
        # Проверяем, что неделя не в прошлом
        if end_date >= today:
            weeks.append({
                'offset': week_offset,
                'start_date': start_date,
                'end_date': end_date,
                'display': format_week_display(week_offset)
            })

    return weeks


def get_week_dates(week_offset=0):
    """Возвращает даты для указанной недели (исключая воскресенья)"""
    start_date, end_date = get_week_range(week_offset)
    today = datetime.now().date()

    dates = []
    current = start_date

    while current <= end_date:
        # Исключаем воскресенья и даты в прошлом
        if current.weekday() != 6 and current >= today:
            dates.append(current)
        current += timedelta(days=1)

    return dates


def get_week_range(week_offset=0):
    """Возвращает диапазон дат для указанной недели (пн-сб)"""
    today = datetime.now().date()

    # Находим понедельник текущей недели
    current_weekday = today.weekday()
    monday = today - timedelta(days=current_weekday)

    # Смещаем на нужное количество недель
    start_date = monday + timedelta(weeks=week_offset)
    end_date = start_date + timedelta(days=5)  # до субботы

    return start_date, end_date


def format_date_display(date):
    """Форматирует дату для отображения"""
    days_ru = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    months_ru = ['янв', 'фев', 'мар', 'апр', 'май', 'июн',
                 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']

    day_name = days_ru[date.weekday()]
    return f"{day_name}, {date.day} {months_ru[date.month - 1]}"


def format_week_display(week_offset=0):
    """Форматирует отображение недели"""
    start_date, end_date = get_week_range(week_offset)

    months_ru = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']

    if start_date.month == end_date.month:
        return f"{start_date.day}-{end_date.day} {months_ru[start_date.month - 1]}"
    else:
        return f"{start_date.day} {months_ru[start_date.month - 1]} - {end_date.day} {months_ru[end_date.month - 1]}"


def is_working_day(date):
    """Проверяет, является ли день рабочим (исключаем воскресенья)"""
    weekday = date.weekday()
    return weekday != 6  # Не воскресенье


def get_working_hours_for_date(date):
    """Возвращает рабочие часы для указанной даты"""
    weekday = date.weekday()

    if weekday <= 3:  # Пн-Чт
        return WORKING_HOURS['mon-thu']
    elif weekday == 4:  # Пт
        return WORKING_HOURS['fri']
    elif weekday == 5:  # Сб
        return WORKING_HOURS['sat']
    else:  # Вс
        return None


def can_book_at_time(date, time):
    """Проверяет, можно ли бронировать на указанное время"""
    working_hours = get_working_hours_for_date(date)
    if not working_hours:
        return False

    hour = time.hour
    minute = time.minute

    # Для сегодняшнего дня проверяем, что время не в прошлом
    today = datetime.now().date()
    now = datetime.now().time()

    if date == today:
        if hour < now.hour:
            return False
        if hour == now.hour and minute <= now.minute:
            return False

    return working_hours['start'] <= hour < working_hours['end']


def is_booking_within_working_hours(date, start_time, duration_hours):
    """Проверяет, что бронирование полностью в пределах рабочих часов"""
    working_hours = get_working_hours_for_date(date)
    if not working_hours:
        return False

    start_hour = start_time.hour
    end_hour = start_hour + duration_hours

    # Проверяем, что начало и конец брони в рабочих часах
    return (working_hours['start'] <= start_hour and
            end_hour <= working_hours['end'])


def get_available_end_times(date, start_time):
    """Возвращает доступные варианты окончания бронирования (без ограничения по часам)"""
    working_hours = get_working_hours_for_date(date)
    if not working_hours:
        return []

    start_hour = start_time.hour
    available_durations = []

    # Максимальная длительность - до конца рабочего дня
    max_duration = working_hours['end'] - start_hour

    # Создаем варианты от 1 часа до максимальной длительности
    for hours in range(1, max_duration + 1):
        available_durations.append(hours)

    return available_durations


def get_current_datetime():
    """Возвращает текущие дату и время"""
    return datetime.now()