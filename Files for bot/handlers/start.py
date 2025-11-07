from aiogram import Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from keyboards import get_student_keyboard, get_main_menu_keyboard, get_yes_no_keyboard, get_contact_keyboard
from database import Database
from states import RegistrationStates

db = Database()



async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start с проверкой регистрации"""
    await state.clear()

    # Проверяем, зарегистрирован ли пользователь
    user = await db.get_user(message.from_user.id)

    if user:
        # Пользователь уже зарегистрирован
        await message.answer(
            "✅ Вы уже зарегистрированы в системе!\n\n"
            "🏠 Главное меню:",
            reply_markup=get_main_menu_keyboard(message.from_user.id)
        )
    else:
        # Начинаем регистрацию
        await message.answer(
            "🎓 Добро пожаловать в систему бронирования лектория МАИ!\n"
            "Этот Бот создан для бронирования лектория, компьютеров, Playstation\n"
            "Если вы не являетесь студентом МАИ, то вы не сможете попасть в лекторий, т.к он предназначен только для студентов.\n"
            "Вы являетесь студентом МАИ?",
            reply_markup=get_student_keyboard()
        )


async def cmd_help(message: Message):
    await show_help_message(message)


async def show_help(callback: CallbackQuery):
    await show_help_message(callback.message)
    await callback.answer()


async def show_help_message(message_source):
    help_text = """
🤖 *Доступные команды:*

*/start* - Начать работу с ботом
*/help* - Показать эту справку
*/book* - Начать бронирование

📋 *Основные функции:*
• Бронирование оборудования (настольные игры, PlayStation, теннис, компьютеры)
• Просмотр своих бронирований
• Отмена бронирований
• Просмотр профиля и его редактирование

⚙️ *Для администраторов:*
• Просмотр статистики
• Управление пользователями
• Просмотр всех бронирований

⏰ *Часы работы коворкинга:*
Пн-Чт: 16:00 - 22:00
Пт: 17:00 - 22:00
Сб: 14:00 - 19:00
Вс: выходной

📞 *По вопросам обращайтесь к администраторам.*
    """
    await message_source.answer(help_text, parse_mode="Markdown")


async def process_student_yes(callback: CallbackQuery, state: FSMContext):
    await state.update_data(is_student=True)
    await callback.message.answer("✅ Отлично! При входе нужно будет предоставить студенческий пропуск.")
    await ask_for_name(callback.message, state)
    await callback.answer()


async def process_student_no(callback: CallbackQuery, state: FSMContext):
    await state.update_data(is_student=False)
    await callback.message.answer("👋 Вы можете пользоваться коворкингом как гость.")
    await ask_for_name(callback.message, state)
    await callback.answer()


async def ask_for_name(message_source, state: FSMContext):
    """Запрос имени пользователя"""
    await message_source.answer(
        "👤 Как вас зовут?\n\n"
        "Введите ваше имя и фамилию (например: Иван Иванов):",
        reply_markup=None
    )
    await state.set_state(RegistrationStates.waiting_for_full_name)


async def process_full_name(message: Message, state: FSMContext):
    """Обработка введенного имени с подтверждением"""
    full_name = message.text.strip()
    if len(full_name.split()) < 2:
        await message.answer("❌ Пожалуйста, введите имя и фамилию через пробел (например: Иван Иванов):")
        return

    await state.update_data(full_name=full_name)

    # Подтверждаем имя
    await message.answer(
        f"🤔 Вас зовут *{full_name}*?",
        parse_mode="Markdown",
        reply_markup=get_yes_no_keyboard()
    )
    await state.set_state(RegistrationStates.waiting_for_name_confirmation)


async def process_name_confirmation_yes(callback: CallbackQuery, state: FSMContext):
    """Подтверждение имени - переход к вводу телефона"""
    await callback.message.answer(
        "📱 Теперь поделитесь своим контактом:",
        reply_markup=get_contact_keyboard()
    )
    await state.set_state(RegistrationStates.waiting_for_contact)
    await callback.answer()


async def process_name_confirmation_no(callback: CallbackQuery, state: FSMContext):
    """Отказ от имени - запрашиваем заново"""
    await callback.message.answer(
        "👤 Введите ваше имя и фамилию заново (например: Иван Иванов):"
    )
    await state.set_state(RegistrationStates.waiting_for_full_name)
    await callback.answer()


async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(
        "🏠 Главное меню:",
        reply_markup=get_main_menu_keyboard(callback.from_user.id)
    )
    await callback.answer()


def register_start_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.callback_query.register(show_help, F.data == "show_help")
    dp.callback_query.register(process_student_yes, F.data == "student_yes")
    dp.callback_query.register(process_student_no, F.data == "student_no")
    dp.callback_query.register(process_name_confirmation_yes, F.data == "name_yes")
    dp.callback_query.register(process_name_confirmation_no, F.data == "name_no")
    dp.callback_query.register(back_to_main, F.data == "back_to_main")
    dp.message.register(process_full_name, RegistrationStates.waiting_for_full_name)