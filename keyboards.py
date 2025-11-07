from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from helpers import get_available_weeks, get_week_dates, format_date_display, format_week_display

BOOKING_TYPES = [
    "Лекторий",
    "Плейстейшн",
    "Компьютеры"
]

ADMINS = [123456789]


def get_student_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="student_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="student_no")
        ]
    ])


def get_weeks_keyboard():
    """Клавиатура для выбора недели"""
    weeks = get_available_weeks()
    buttons = []

    for week in weeks:
        if week['offset'] == 0:
            display_text = f"📅 Текущая неделя ({week['display']})"
        else:
            display_text = f"📅 {week['display']}"

        buttons.append([
            InlineKeyboardButton(
                text=display_text,
                callback_data=f"select_week_{week['offset']}"
            )
        ])

    buttons.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_week_dates_keyboard(week_offset):
    """Клавиатура с датами выбранной недели"""
    dates = get_week_dates(week_offset)
    buttons = []

    # Группируем даты по 3 в строке
    for i in range(0, len(dates), 3):
        row = []
        for j in range(3):
            if i + j < len(dates):
                date = dates[i + j]
                button_text = format_date_display(date)
                callback_data = f"select_date_{date.strftime('%Y-%m-%d')}"
                row.append(InlineKeyboardButton(text=button_text, callback_data=callback_data))
        if row:
            buttons.append(row)

    buttons.append([InlineKeyboardButton(text="🔙 Назад к выбору недели", callback_data="book_now")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_booking_type_keyboard():
    """Клавиатура с 3 типами бронирования"""
    buttons = [
        [KeyboardButton(text="Лекторий")],
        [KeyboardButton(text="Плейстейшн")],
        [KeyboardButton(text="Компьютеры")],
        [KeyboardButton(text="🔙 Назад к выбору даты")]
    ]

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )


def get_contact_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_main_menu_keyboard(user_id):
    """Главное меню с учетом прав администратора"""
    buttons = [
        [
            InlineKeyboardButton(text="📅 Забронировать", callback_data="book_now"),
            InlineKeyboardButton(text="📋 Мои брони", callback_data="view_my_bookings")
        ],
        [
            InlineKeyboardButton(text="❌ Отменить бронь", callback_data="cancel_booking")
        ],
        [
            InlineKeyboardButton(text="🔍 Фильтр броней", callback_data="view_bookings_filter"),
        ],
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="view_profile"),
            InlineKeyboardButton(text="❓ Помощь", callback_data="show_help")
        ]
    ]

    # Добавляем кнопку администраторов
    if user_id in ADMINS:
        buttons.append([
            InlineKeyboardButton(text="⚙️ Администратор", callback_data="admin_panel")
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_profile_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Изменить имя", callback_data="edit_name"),
            InlineKeyboardButton(text="📱 Изменить телефон", callback_data="edit_phone")
        ],
        [
            InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")
        ]
    ])


def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="👥 Все пользователи", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(text="📋 Все бронирования", callback_data="admin_all_bookings"),
            InlineKeyboardButton(text="🗑️ Очистить старые", callback_data="admin_cleanup")
        ],
        [
            InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")
        ]
    ])


def get_cancel_booking_keyboard(bookings):
    from helpers import format_date_display

    buttons = []
    for booking in bookings:
        display_date = format_date_display(booking['booking_date'])
        buttons.append([
            InlineKeyboardButton(
                text=f"{booking['booking_type']} - {display_date} {booking['start_time']}",
                callback_data=f"cancel_{booking['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_to_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")]
    ])


def get_time_keyboard(available_times):
    buttons = []

    for i in range(0, len(available_times), 4):
        row = []
        for j in range(4):
            if i + j < len(available_times):
                row.append(KeyboardButton(text=available_times[i + j]))
        if row:
            buttons.append(row)

    buttons.append([KeyboardButton(text="🔙 Назад к выбору типа")])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )


def get_duration_keyboard(available_durations):
    """Клавиатура для выбора длительности бронирования"""
    buttons = []

    # Группируем длительности по 3 в строке
    for i in range(0, len(available_durations), 3):
        row = []
        for j in range(3):
            if i + j < len(available_durations):
                hours = available_durations[i + j]
                row.append(KeyboardButton(text=f"{hours} час(а)"))
        if row:
            buttons.append(row)

    buttons.append([KeyboardButton(text="🔙 Назад к выбору времени")])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )


def get_yes_no_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="name_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="name_no")
        ]
    ])


def get_join_decision_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, присоединиться", callback_data="join_yes"),
            InlineKeyboardButton(text="❌ Нет, выбрать другое время", callback_data="join_no")
        ]
    ])