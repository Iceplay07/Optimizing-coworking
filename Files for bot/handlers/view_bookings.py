from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ViewBookingsStates(StatesGroup):
    waiting_for_filter_week = State()
    waiting_for_filter_date = State()
    waiting_for_filter_type = State()


BOOKING_TYPES = [
    "Лекторий",
    "Плейстейшн",
    "Компьютеры"
]


def get_filter_weeks_keyboard():
    """Клавиатура для выбора недели в фильтре"""
    from helpers import get_available_weeks, format_week_display

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
                callback_data=f"filter_week_{week['offset']}"
            )
        ])

    buttons.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_filter_dates_keyboard(week_offset):
    """Клавиатура с датами выбранной недели для фильтра"""
    from helpers import get_week_dates, format_date_display

    dates = get_week_dates(week_offset)
    buttons = []

    # Группируем даты по 3 в строке
    for i in range(0, len(dates), 3):
        row = []
        for j in range(3):
            if i + j < len(dates):
                date = dates[i + j]
                button_text = format_date_display(date)
                callback_data = f"filter_date_{date.strftime('%Y-%m-%d')}"
                row.append(InlineKeyboardButton(text=button_text, callback_data=callback_data))
        if row:
            buttons.append(row)

    buttons.append([InlineKeyboardButton(text="🔙 Назад к выбору недели", callback_data="view_bookings_filter")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_filter_types_keyboard():
    """Клавиатура для выбора типа в фильтре"""
    buttons = []
    buttons.append([InlineKeyboardButton(text="📋 Все типы", callback_data="filter_type_all")])

    for booking_type in BOOKING_TYPES:
        buttons.append([InlineKeyboardButton(text=booking_type, callback_data=f"filter_type_{booking_type}")])

    buttons.append([InlineKeyboardButton(text="🔙 Назад к выбору даты", callback_data="view_bookings_filter")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def start_view_bookings_filter(callback: CallbackQuery, state: FSMContext):
    """Начало процесса фильтрации бронирований"""
    try:
        await state.clear()
        await callback.message.answer(
            "📅 Выберите неделю для просмотра бронирований:",
            reply_markup=get_filter_weeks_keyboard()
        )
        await state.set_state(ViewBookingsStates.waiting_for_filter_week)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in start_view_bookings_filter: {e}")
        await callback.message.answer("❌ Ошибка при запуске фильтрации бронирований.")


async def process_filter_week(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора недели в фильтре"""
    try:
        week_offset = int(callback.data.replace('filter_week_', ''))

        from helpers import get_week_dates, format_week_display

        await state.update_data(filter_week_offset=week_offset)

        dates = get_week_dates(week_offset)

        if not dates:
            await callback.message.answer("❌ На выбранной неделе нет доступных дат.")
            await callback.answer()
            return

        await callback.message.answer(
            f"📅 Неделя: {format_week_display(week_offset)}\n"
            f"Выберите день для просмотра бронирований:",
            reply_markup=get_filter_dates_keyboard(week_offset)
        )
        await state.set_state(ViewBookingsStates.waiting_for_filter_date)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in process_filter_week: {e}")
        await callback.message.answer("❌ Ошибка при выборе недели.")


async def process_filter_date(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора даты в фильтре"""
    try:
        date_str = callback.data.replace('filter_date_', '')
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        await state.update_data(filter_date=selected_date)

        from helpers import format_date_display

        await callback.message.answer(
            f"📅 Выбрана дата: {format_date_display(selected_date)}\n"
            f"🎯 Выберите тип бронирования для просмотра:",
            reply_markup=get_filter_types_keyboard()
        )
        await state.set_state(ViewBookingsStates.waiting_for_filter_type)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in process_filter_date: {e}")
        await callback.message.answer("❌ Ошибка при выборе даты.")


async def process_filter_type(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора типа и отображение результатов"""
    try:
        from database import Database
        db = Database()

        user_data = await state.get_data()
        selected_date = user_data.get('filter_date')

        if not selected_date:
            await callback.message.answer("❌ Ошибка: дата не выбрана. Начните заново.")
            await state.clear()
            await callback.answer()
            return

        if callback.data == "filter_type_all":
            booking_type = None
            display_type = "Все типы"
        else:
            booking_type = callback.data.replace("filter_type_", "")
            display_type = booking_type

        # Получаем бронирования для выбранной даты и типа
        bookings = await db.get_bookings_by_date_and_type(selected_date, booking_type)

        if not bookings:
            from helpers import format_date_display
            await callback.message.answer(
                f"📭 На {format_date_display(selected_date)} для типа '{display_type}' бронирований не найдено."
            )
            await state.clear()
            await callback.answer()
            return

        # Форматируем результат
        from helpers import format_date_display
        response = f"📋 *Бронирования на {format_date_display(selected_date)} ({display_type}):*\n\n"

        # Группируем по типам
        bookings_by_type = {}
        for booking in bookings:
            booking_type = booking['booking_type']
            if booking_type not in bookings_by_type:
                bookings_by_type[booking_type] = []
            bookings_by_type[booking_type].append(booking)

        # Выводим бронирования по типам
        for booking_type, type_bookings in bookings_by_type.items():
            response += f"🎯 *{booking_type}:*\n"

            for booking in type_bookings:
                response += (
                    f"👤 {booking['full_name']}\n"
                    f"🕒 {booking['start_time'].strftime('%H:%M')} - {booking['end_time'].strftime('%H:%M')}\n"
                    f"---\n"
                )

            response += "\n"

        # Статистика
        total_bookings = len(bookings)
        unique_users = len(set(booking['user_id'] for booking in bookings))
        response += f"📊 *Статистика:* {total_bookings} бронирований, {unique_users} пользователей"

        from keyboards import get_main_menu_keyboard
        await callback.message.answer(response, parse_mode="Markdown")
        await callback.message.answer(
            "🏠 Главное меню:",
            reply_markup=get_main_menu_keyboard(callback.from_user.id)
        )
        await state.clear()
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in process_filter_type: {e}")
        await callback.message.answer("❌ Ошибка при отображении бронирований.")
        await state.clear()


def register_view_bookings_handlers(dp: Dispatcher):
    """Регистрация обработчиков"""
    dp.callback_query.register(start_view_bookings_filter, F.data == "view_bookings_filter")
    dp.callback_query.register(process_filter_week, ViewBookingsStates.waiting_for_filter_week,
                               F.data.startswith("filter_week_"))
    dp.callback_query.register(process_filter_date, ViewBookingsStates.waiting_for_filter_date,
                               F.data.startswith("filter_date_"))
    dp.callback_query.register(process_filter_type, ViewBookingsStates.waiting_for_filter_type,
                               F.data.startswith("filter_type_"))


