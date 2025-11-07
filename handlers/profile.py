from aiogram import Dispatcher, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import Database
from keyboards import get_main_menu_keyboard, get_profile_keyboard, get_contact_keyboard

db = Database()


class ProfileStates(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_new_phone = State()


async def view_profile(callback: CallbackQuery):
    """Показать профиль пользователя"""
    user_id = callback.from_user.id

    # Получаем данные пользователя из базы
    user = await db.get_user(user_id)

    if not user:
        await callback.message.answer(
            "❌ Вы не зарегистрированы в системе. Пожалуйста, начните с команды /start"
        )
        await callback.answer()
        return

    # Получаем бронирования пользователя
    user_bookings = await db.get_user_bookings(user_id, active_only=False)
    active_bookings = await db.get_user_bookings(user_id, active_only=True)

    profile_text = (
        f"👤 *Ваш профиль:*\n\n"
        f"🆔 ID: `{user_id}`\n"
        f"📛 Имя: {user['full_name']}\n"
        f"📞 Телефон: {user['phone']}\n"
        f"🎓 Статус: {'✅ Студент МАИ' if user['is_student'] else '❌ Не студент'}\n"
        f"📅 Дата регистрации: {user['created_at'].strftime('%d.%m.%Y')}\n\n"
        f"📊 Статистика бронирований:\n"
        f"• Всего бронирований: {len(user_bookings)}\n"
        f"• Активных бронирований: {len(active_bookings)}\n"
        f"• Отмененных бронирований: {len([b for b in user_bookings if b['status'] == 'cancelled'])}\n"
        f"• Завершенных бронирований: {len([b for b in user_bookings if b['status'] == 'expired'])}"
    )

    await callback.message.answer(profile_text, parse_mode="Markdown", reply_markup=get_profile_keyboard())
    await callback.answer()


async def edit_profile(callback: CallbackQuery):
    """Начать редактирование профиля"""
    await callback.message.answer(
        "✏️ *Редактирование профиля*\n\n"
        "Выберите что хотите изменить:",
        parse_mode="Markdown",
        reply_markup=get_profile_keyboard()
    )
    await callback.answer()


async def edit_name_start(callback: CallbackQuery, state: FSMContext):
    """Начать изменение имени"""
    await callback.message.answer(
        "📛 Введите ваше новое имя и фамилию:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(ProfileStates.waiting_for_new_name)
    await callback.answer()


async def process_new_name(message: Message, state: FSMContext):
    """Обработать новое имя"""
    new_name = message.text.strip()
    if len(new_name.split()) < 2:
        await message.answer("❌ Пожалуйста, введите имя и фамилию через пробел:")
        return

    # Обновляем имя в базе данных
    user = await db.get_user(message.from_user.id)
    if user:
        await db.add_user(
            user_id=message.from_user.id,
            full_name=new_name,
            phone=user['phone'],
            is_student=user['is_student']
        )

    await message.answer(f"✅ Имя успешно изменено на: {new_name}")

    await message.answer(
        "🏠 Главное меню:",
        reply_markup=get_main_menu_keyboard(message.from_user.id)
    )
    await state.clear()


async def edit_phone_start(callback: CallbackQuery, state: FSMContext):
    """Начать изменение телефона"""
    await callback.message.answer(
        "📱 Поделитесь вашим новым контактом:",
        reply_markup=get_contact_keyboard()
    )
    await state.set_state(ProfileStates.waiting_for_new_phone)
    await callback.answer()


async def process_new_phone(message: Message, state: FSMContext):
    """Обработать новый телефон"""
    if message.contact:
        new_phone = message.contact.phone_number

        # Обновляем телефон в базе данных
        user = await db.get_user(message.from_user.id)
        if user:
            await db.add_user(
                user_id=message.from_user.id,
                full_name=user['full_name'],
                phone=new_phone,
                is_student=user['is_student']
            )

        await message.answer(
            f"✅ Номер телефона успешно изменен на: {new_phone}",
            reply_markup=ReplyKeyboardRemove()
        )

        await message.answer(
            "🏠 Главное меню:",
            reply_markup=get_main_menu_keyboard(message.from_user.id)
        )
        await state.clear()
    else:
        await message.answer("❌ Пожалуйста, поделитесь контактом используя кнопку:")


def register_profile_handlers(dp: Dispatcher):
    dp.callback_query.register(view_profile, F.data == "view_profile")
    dp.callback_query.register(edit_profile, F.data == "edit_profile")
    dp.callback_query.register(edit_name_start, F.data == "edit_name")
    dp.callback_query.register(edit_phone_start, F.data == "edit_phone")
    dp.message.register(process_new_name, ProfileStates.waiting_for_new_name)
    dp.message.register(process_new_phone, ProfileStates.waiting_for_new_phone)