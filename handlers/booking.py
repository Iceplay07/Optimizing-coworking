from aiogram import Dispatcher, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import logging

from states import BookingStates
from database import Database
from config import BOOKING_TYPES, BOOKING_CAPACITY, JOINABLE_ACTIVITIES
from helpers import get_current_datetime

logger = logging.getLogger(__name__)
db = Database()


async def check_user_registration(user_id):
    """Проверяет, зарегистрирован ли пользователь"""
    try:
        logger.info(f"Checking registration for user_id: {user_id}")
        user = await db.get_user(user_id)
        is_registered = user is not None
        logger.info(f"User {user_id} registered: {is_registered}")
        return is_registered
    except Exception as e:
        logger.error(f"Error checking user registration for {user_id}: {e}")
        return False


async def start_booking(callback: CallbackQuery, state: FSMContext):
    """Начало процесса бронирования - выбор недели"""
    logger.info("=== START BOOKING PROCESS ===")

    user_id = callback.from_user.id
    # Проверяем, зарегистрирован ли пользователь
    if not await check_user_registration(user_id):
        await callback.message.answer(
            "❌ Вы не зарегистрированы в системе. Пожалуйста, начните с команды /start"
        )
        await callback.answer()
        return

    await state.clear()

    from keyboards import get_weeks_keyboard
    from helpers import get_available_weeks

    weeks = get_available_weeks()

    if not weeks:
        from keyboards import get_main_menu_keyboard
        await callback.message.answer(
            "❌ Нет доступных недель для бронирования.",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        await callback.answer()
        return

    week_list = "\n".join([f"• {week['display']}" for week in weeks])

    await callback.message.answer(
        f"📅 Выберите неделю для бронирования:\n\n{week_list}",
        reply_markup=get_weeks_keyboard()
    )
    await state.set_state(BookingStates.waiting_for_booking_week)
    await callback.answer()


async def process_booking_week(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора недели"""
    try:
        logger.info(f"=== PROCESS BOOKING WEEK: {callback.data} ===")

        user_id = callback.from_user.id
        # Проверяем, зарегистрирован ли пользователь
        if not await check_user_registration(user_id):
            await callback.message.answer(
                "❌ Вы не зарегистрированы в системе. Пожалуйста, начните с команды /start"
            )
            await state.clear()
            await callback.answer()
            return

        week_offset = int(callback.data.replace('select_week_', ''))

        await state.update_data(week_offset=week_offset)
        logger.info(f"Week offset saved: {week_offset}")

        from keyboards import get_week_dates_keyboard
        from helpers import get_week_dates, format_week_display

        dates = get_week_dates(week_offset)

        if not dates:
            await callback.message.answer(
                "❌ На выбранной неделе нет доступных дат.",
                reply_markup=get_weeks_keyboard()
            )
            await callback.answer()
            return

        await callback.message.answer(
            f"📅 Неделя: {format_week_display(week_offset)}\n"
            f"Выберите день для бронирования:",
            reply_markup=get_week_dates_keyboard(week_offset)
        )
        await state.set_state(BookingStates.waiting_for_booking_date)

    except Exception as e:
        logger.error(f"Error in process_booking_week: {e}", exc_info=True)
        await callback.message.answer("❌ Ошибка при выборе недели. Попробуйте снова.")
        await state.clear()
    finally:
        await callback.answer()


async def process_booking_date(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора даты"""
    try:
        logger.info(f"=== PROCESS BOOKING DATE: {callback.data} ===")

        user_id = callback.from_user.id
        # Проверяем, зарегистрирован ли пользователь
        if not await check_user_registration(user_id):
            await callback.message.answer(
                "❌ Вы не зарегистрированы в системе. Пожалуйста, начните с команды /start"
            )
            await state.clear()
            await callback.answer()
            return

        date_str = callback.data.replace('select_date_', '')
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Проверяем, что дата не в прошлом
        today = datetime.now().date()
        if booking_date < today:
            await callback.message.answer(
                "❌ Нельзя выбрать прошедшую дату. Пожалуйста, выберите другую дату.",
                reply_markup=get_weeks_keyboard()
            )
            await state.clear()
            await callback.answer()
            return

        await state.update_data(booking_date=booking_date)
        logger.info(f"Date saved: {booking_date}")

        # Получаем доступные типы бронирования для пользователя на эту дату
        available_types = await get_available_booking_types(user_id, booking_date)

        if not available_types:
            from keyboards import get_main_menu_keyboard

            await callback.message.answer(
                "❌ На выбранную дату у вас уже есть бронирования всех типов. "
                "Вы можете забронировать каждый тип только один раз в день.\n\n"
                "Выберите другую дату или отмените существующее бронирование.",
                reply_markup=get_main_menu_keyboard(user_id)
            )
            await state.clear()
            await callback.answer()
            return

        from keyboards import get_booking_type_keyboard

        await callback.message.answer(
            f"📅 Выбрана дата: {booking_date.strftime('%d.%m.%Y')}\n"
            f"🎯 Что вы хотите забронировать?",
            reply_markup=get_booking_type_keyboard()
        )
        await state.set_state(BookingStates.waiting_for_booking_type)

    except Exception as e:
        logger.error(f"Error in process_booking_date: {e}", exc_info=True)
        await callback.message.answer("❌ Ошибка при выборе даты. Попробуйте снова.")
        await state.clear()
    finally:
        await callback.answer()


async def get_available_booking_types(user_id, booking_date):
    """Возвращает доступные типы бронирования для пользователя на указанную дату"""
    try:
        available_types = []
        for booking_type in BOOKING_TYPES:
            has_booking = await db.has_booking_type_on_date(user_id, booking_type, booking_date)
            if not has_booking:
                available_types.append(booking_type)
        return available_types
    except Exception as e:
        logger.error(f"Error getting available types: {e}")
        return BOOKING_TYPES[:]


async def process_booking_type(message: Message, state: FSMContext):
    """Обработка выбора типа бронирования"""
    try:
        logger.info(f"=== PROCESS BOOKING TYPE: '{message.text}' ===")

        user_id = message.from_user.id
        # Проверяем, зарегистрирован ли пользователь
        if not await check_user_registration(user_id):
            await message.answer(
                "❌ Вы не зарегистрированы в системе. Пожалуйста, начните с команды /start"
            )
            await state.clear()
            return

        if message.text == "🔙 Назад к выбору даты":
            from keyboards import get_weeks_keyboard
            await message.answer(
                "📅 Выберите неделю для бронирования:",
                reply_markup=get_weeks_keyboard()
            )
            await state.set_state(BookingStates.waiting_for_booking_week)
            return

        booking_type = message.text
        if booking_type not in BOOKING_TYPES:
            await message.answer("❌ Пожалуйста, выберите тип бронирования из предложенных вариантов:")
            return

        user_data = await state.get_data()
        booking_date = user_data.get('booking_date')

        if not booking_date:
            await message.answer("❌ Ошибка: дата не выбрана. Начните заново.")
            await state.clear()
            return

        # Проверяем, не забронировал ли пользователь уже этот тип на выбранную дату
        has_booking = await db.has_booking_type_on_date(user_id, booking_type, booking_date)
        if has_booking:
            await message.answer(
                "❌ У вас уже есть бронь этого типа на выбранную дату. "
                "Выберите другой тип или дату."
            )
            return

        await state.update_data(booking_type=booking_type)
        logger.info(f"Booking type saved: {booking_type}")

        from helpers import get_working_hours_for_date

        # Определяем рабочие часы для дня недели
        working_hours = get_working_hours_for_date(booking_date)
        if not working_hours:
            await message.answer("❌ В этот день коворкинг не работает. Выберите другую дату.")
            await state.clear()
            return

        start_hour = working_hours['start']
        end_hour = working_hours['end']

        # Если выбран сегодняшний день, не показываем прошедшее время
        today = datetime.now().date()
        current_time = datetime.now().time()
        current_hour = current_time.hour

        available_times = []
        for hour in range(start_hour, end_hour):
            # Для сегодняшнего дня пропускаем прошедшие часы
            if today == booking_date:
                if hour < current_hour:
                    continue
                # Если текущий час, проверяем минуты
                if hour == current_hour and current_time.minute > 0:
                    continue
            available_times.append(f"{hour:02d}:00")

        if not available_times:
            await message.answer("❌ На сегодня больше нет доступного времени. Выберите другую дату.")
            await state.clear()
            return

        # Создаем клавиатуру с временами
        time_rows = []
        for i in range(0, len(available_times), 4):
            time_rows.append([KeyboardButton(text=time) for time in available_times[i:i + 4]])
        time_rows.append([KeyboardButton(text="🔙 Назад к выбору типа")])

        keyboard = ReplyKeyboardMarkup(
            keyboard=time_rows,
            resize_keyboard=True
        )

        await message.answer(
            "🕒 Выберите время начала бронирования:",
            reply_markup=keyboard
        )
        await state.set_state(BookingStates.waiting_for_booking_time)

    except Exception as e:
        logger.error(f"Error in process_booking_type: {e}", exc_info=True)
        await message.answer("❌ Ошибка при выборе типа бронирования. Попробуйте снова.")
        await state.clear()


async def process_booking_time(message: Message, state: FSMContext):
    """Обработка выбора времени"""
    try:
        logger.info(f"=== PROCESS BOOKING TIME: '{message.text}' ===")

        user_id = message.from_user.id
        # Проверяем, зарегистрирован ли пользователь
        if not await check_user_registration(user_id):
            await message.answer(
                "❌ Вы не зарегистрированы в системе. Пожалуйста, начните с команды /start"
            )
            await state.clear()
            return

        if message.text == "🔙 Назад к выбору типа":
            user_data = await state.get_data()
            booking_date = user_data.get('booking_date')

            if not booking_date:
                await message.answer("❌ Ошибка: дата не найдена. Начните заново.")
                await state.clear()
                return

            from keyboards import get_booking_type_keyboard

            await message.answer(
                f"📅 Дата: {booking_date.strftime('%d.%m.%Y')}\n"
                f"🎯 Что вы хотите забронировать?",
                reply_markup=get_booking_type_keyboard()
            )
            await state.set_state(BookingStates.waiting_for_booking_type)
            return

        try:
            start_time = datetime.strptime(message.text, "%H:%M").time()
            logger.info(f"Time parsed: {start_time}")
        except ValueError:
            await message.answer("❌ Пожалуйста, выберите время из предложенных вариантов:")
            return

        user_data = await state.get_data()
        booking_date = user_data.get('booking_date')

        if not booking_date:
            await message.answer("❌ Ошибка: дата не найдена. Начните заново.")
            await state.clear()
            return

        from helpers import can_book_at_time

        # Проверяем, доступно ли время для бронирования
        if not can_book_at_time(booking_date, start_time):
            await message.answer("❌ Выбранное время недоступно для бронирования. Выберите другое время:")
            return

        await state.update_data(start_time=start_time)

        from helpers import get_available_end_times

        # Получаем доступные длительности для выбранного времени (без ограничений)
        available_durations = get_available_end_times(booking_date, start_time)

        if not available_durations:
            await message.answer("❌ Для выбранного времени нет доступных длительностей бронирования.")
            return

        from keyboards import get_duration_keyboard

        await message.answer(
            f"⏱ Выберите длительность бронирования (доступно до {max(available_durations)} часа):",
            reply_markup=get_duration_keyboard(available_durations)
        )
        await state.set_state(BookingStates.waiting_for_duration)

    except Exception as e:
        logger.error(f"Error in process_booking_time: {e}", exc_info=True)
        await message.answer("❌ Ошибка при выборе времени. Попробуйте снова.")
        await state.clear()


async def process_duration(message: Message, state: FSMContext):
    """Обработка выбора длительности с проверкой пересечений"""
    try:
        logger.info(f"=== PROCESS DURATION: '{message.text}' ===")

        user_id = message.from_user.id
        # Проверяем, зарегистрирован ли пользователь
        if not await check_user_registration(user_id):
            await message.answer(
                "❌ Вы не зарегистрированы в системе. Пожалуйста, начните с команды /start"
            )
            await state.clear()
            return

        if message.text == "🔙 Назад к выбору времени":
            user_data = await state.get_data()
            booking_date = user_data.get('booking_date')

            if not booking_date:
                await message.answer("❌ Ошибка: дата не найдена. Начните заново.")
                await state.clear()
                return

            from helpers import get_working_hours_for_date

            working_hours = get_working_hours_for_date(booking_date)
            if not working_hours:
                await message.answer("❌ Ошибка: рабочие часы не найдены.")
                await state.clear()
                return

            available_times = []
            today = datetime.now().date()
            current_time = datetime.now().time()
            current_hour = current_time.hour

            for hour in range(working_hours['start'], working_hours['end']):
                if today == booking_date:
                    if hour < current_hour:
                        continue
                    if hour == current_hour and current_time.minute > 0:
                        continue
                available_times.append(f"{hour:02d}:00")

            # Группируем времена по 4 в строке
            time_rows = []
            for i in range(0, len(available_times), 4):
                time_rows.append([KeyboardButton(text=time) for time in available_times[i:i + 4]])
            time_rows.append([KeyboardButton(text="🔙 Назад к выбору типа")])

            # Создаем клавиатуру для возврата
            keyboard = ReplyKeyboardMarkup(
                keyboard=time_rows,
                resize_keyboard=True
            )

            await message.answer(
                "🕒 Выберите время начала бронирования:",
                reply_markup=keyboard
            )
            await state.set_state(BookingStates.waiting_for_booking_time)
            return

        try:
            # Извлекаем число из текста (например, "2 час(а)" -> 2)
            duration = int(''.join(filter(str.isdigit, message.text)))
            logger.info(f"Duration parsed: {duration}")
        except (ValueError, IndexError):
            await message.answer("❌ Пожалуйста, выберите длительность из предложенных вариантов:")
            return

        user_data = await state.get_data()
        booking_date = user_data.get('booking_date')
        start_time = user_data.get('start_time')
        booking_type = user_data.get('booking_type')

        if not booking_date or not start_time:
            await message.answer("❌ Ошибка: данные бронирования не найдены. Начните заново.")
            await state.clear()
            return

        from helpers import is_booking_within_working_hours

        # Проверяем, что бронирование полностью в пределах рабочих часов
        if not is_booking_within_working_hours(booking_date, start_time, duration):
            await message.answer("❌ Бронирование выходит за рамки рабочего времени. Выберите меньшую длительность:")
            return

        # Вычисляем время окончания
        start_datetime = datetime.combine(booking_date, start_time)
        end_datetime = start_datetime + timedelta(hours=duration)
        end_time = end_datetime.time()

        # Проверяем пересечения с другими бронированиями ТОГО ЖЕ ТИПА
        conflicting_bookings = await db.get_conflicting_bookings(booking_date, start_time, end_time, booking_type)

        # Для компьютеров проверяем емкость (16 мест)
        if booking_type == "Компьютеры":
            capacity = BOOKING_CAPACITY.get("Компьютеры", 16)
            current_count = len(conflicting_bookings)

            if current_count >= capacity:
                # Достигнут лимит для компьютеров
                await message.answer(
                    f"❌ На это время уже достигнут лимит бронирований для '{booking_type}'.\n"
                    f"Доступно мест: {capacity}, уже забронировано: {current_count}\n\n"
                    f"Пожалуйста, выберите другое время.",
                    parse_mode="Markdown"
                )
                return

        # Для социальных активностей (не компьютеры) проверяем, можно ли присоединиться
        if booking_type in JOINABLE_ACTIVITIES and conflicting_bookings:
            # Есть пересечения и это социальная активность - предлагаем присоединиться
            conflicting_users = [booking['full_name'] for booking in conflicting_bookings]
            users_list = ", ".join(conflicting_users)

            await state.update_data(
                duration=duration,
                end_time=end_time,
                conflicting_users=conflicting_users
            )

            from keyboards import get_join_decision_keyboard

            await message.answer(
                f"👥 На это время уже есть бронирования *{booking_type}*:\n\n"
                f"📋 Имена: {users_list}\n\n"
                f"Хотите присоединиться к ним?",
                reply_markup=get_join_decision_keyboard(),
                parse_mode="Markdown"
            )
            await state.set_state(BookingStates.waiting_for_join_decision)
            return

        # Нет пересечений или нельзя присоединиться - создаем бронирование
        await create_booking(message, user_id, state, booking_date, start_time, end_time, booking_type)

    except Exception as e:
        logger.error(f"Error in process_duration: {e}", exc_info=True)
        await message.answer("❌ Ошибка при завершении бронирования. Попробуйте снова.")
        await state.clear()


async def process_join_decision(callback: CallbackQuery, state: FSMContext):
    """Обработка решения о присоединении"""
    try:
        user_id = callback.from_user.id
        logger.info(f"Processing join decision for user_id: {user_id}")

        # Проверяем, зарегистрирован ли пользователь
        if not await check_user_registration(user_id):
            await callback.message.answer(
                "❌ Вы не зарегистрированы в системе. Пожалуйста, начните с команды /start"
            )
            await state.clear()
            await callback.answer()
            return

        user_data = await state.get_data()
        logger.info(f"User data in join decision: {user_data}")

        booking_date = user_data.get('booking_date')
        start_time = user_data.get('start_time')
        end_time = user_data.get('end_time')
        booking_type = user_data.get('booking_type')

        # Проверяем наличие всех необходимых данных
        if not all([booking_date, start_time, end_time, booking_type]):
            logger.error("Missing required data for booking creation")
            await callback.message.answer(
                "❌ Ошибка: недостаточно данных для создания бронирования. Начните заново.",
                reply_markup=ReplyKeyboardRemove()
            )
            await state.clear()
            await callback.answer()
            return

        if callback.data == "join_yes":
            # Пользователь согласился присоединиться
            # Для компьютеров еще раз проверяем доступность (на случай, если места закончились)
            if booking_type == "Компьютеры":
                conflicting_bookings = await db.get_conflicting_bookings(booking_date, start_time, end_time,
                                                                         booking_type)
                capacity = BOOKING_CAPACITY.get("Компьютеры", 16)

                if len(conflicting_bookings) >= capacity:
                    await callback.message.answer(
                        "❌ К сожалению, все места уже заняты. Пожалуйста, выберите другое время.",
                        reply_markup=ReplyKeyboardRemove()
                    )
                    await state.clear()
                    await callback.answer()
                    return

            # Создаем бронирование
            await create_booking(callback.message, user_id, state, booking_date, start_time, end_time, booking_type)
        else:
            # Пользователь отказался присоединяться
            await callback.message.answer(
                "🕒 Выберите другое время для бронирования:",
                reply_markup=ReplyKeyboardRemove()
            )

            # Возвращаем к выбору времени
            from helpers import get_working_hours_for_date

            working_hours = get_working_hours_for_date(booking_date)
            available_times = []
            today = datetime.now().date()
            current_time = datetime.now().time()
            current_hour = current_time.hour

            for hour in range(working_hours['start'], working_hours['end']):
                if today == booking_date:
                    if hour < current_hour:
                        continue
                    if hour == current_hour and current_time.minute > 0:
                        continue
                available_times.append(f"{hour:02d}:00")

            time_rows = []
            for i in range(0, len(available_times), 4):
                time_rows.append([KeyboardButton(text=time) for time in available_times[i:i + 4]])
            time_rows.append([KeyboardButton(text="🔙 Назад к выбору типа")])

            keyboard = ReplyKeyboardMarkup(
                keyboard=time_rows,
                resize_keyboard=True
            )

            await callback.message.answer(
                "🕒 Выберите время начала бронирования:",
                reply_markup=keyboard
            )
            await state.set_state(BookingStates.waiting_for_booking_time)

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in process_join_decision: {e}", exc_info=True)
        await callback.message.answer("❌ Ошибка при обработке решения. Попробуйте снова.")
        await state.clear()


async def create_booking(message_source, user_id, state, booking_date, start_time, end_time, booking_type):
    """Создание бронирования (общая функция)"""
    try:
        logger.info(
            f"Creating booking: user_id={user_id}, type={booking_type}, date={booking_date}, time={start_time}-{end_time}")

        # Финальная проверка регистрации
        if not await check_user_registration(user_id):
            await message_source.answer(
                "❌ Вы не зарегистрированы в системе. Пожалуйста, начните с команды /start",
                reply_markup=ReplyKeyboardRemove()
            )
            await state.clear()
            return

        # Сохраняем бронирование
        booking_id = await db.add_booking(
            user_id=user_id,
            booking_type=booking_type,
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time
        )

        logger.info(f"Booking created with ID: {booking_id}")

        # Получаем информацию о других бронированиях того же времени и типа
        conflicting_bookings = await db.get_conflicting_bookings(booking_date, start_time, end_time, booking_type)
        other_users = [booking for booking in conflicting_bookings if booking['user_id'] != user_id]

        from helpers import format_date_display
        from keyboards import get_main_menu_keyboard

        booking_info = (
            f"✅ Бронирование подтверждено!\n\n"
            f"📋 ID: {booking_id}\n"
            f"🎯 Тип: {booking_type}\n"
            f"📅 Дата: {format_date_display(booking_date)}\n"
            f"🕒 Время: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
        )

        # Добавляем информацию о других участниках, если есть
        if other_users:
            other_names = [booking['full_name'] for booking in other_users]
            booking_info += f"\n\n👥 Участники: {', '.join(other_names)}"

        await message_source.answer(booking_info, reply_markup=ReplyKeyboardRemove())

        # Предлагаем посмотреть бронирования
        await message_source.answer(
            "🏠 Главное меню:",
            reply_markup=get_main_menu_keyboard(user_id)
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Error creating booking: {e}", exc_info=True)
        await message_source.answer("❌ Ошибка при создании бронирования. Попробуйте снова.")
        await state.clear()


def register_booking_handlers(dp: Dispatcher):
    dp.callback_query.register(start_booking, F.data == "book_now")
    dp.callback_query.register(process_booking_week, F.data.startswith('select_week_'))
    dp.callback_query.register(process_booking_date, F.data.startswith('select_date_'))
    dp.message.register(process_booking_type, BookingStates.waiting_for_booking_type)
    dp.message.register(process_booking_time, BookingStates.waiting_for_booking_time)
    dp.message.register(process_duration, BookingStates.waiting_for_duration)
    dp.callback_query.register(process_join_decision, BookingStates.waiting_for_join_decision)