from aiogram import Dispatcher
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from states import RegistrationStates
from keyboards import get_main_menu_keyboard
from database import Database

db = Database()


async def process_contact(message: Message, state: FSMContext):
    """Обработка контакта и завершение регистрации"""
    if message.contact:
        phone = message.contact.phone_number
        user_data = await state.get_data()

        await db.add_user(
            user_id=message.from_user.id,
            full_name=user_data['full_name'],
            phone=phone,
            is_student=user_data.get('is_student', False)
        )

        await message.answer(
            "✅ Регистрация завершена! Теперь вы можете забронировать оборудование.",
            reply_markup=ReplyKeyboardRemove()
        )

        await message.answer(
            "🏠 Главное меню:",
            reply_markup=get_main_menu_keyboard(message.from_user.id)
        )

        await state.clear()
    else:
        await message.answer("❌ Пожалуйста, поделитесь контактом используя кнопку:")

def register_registration_handlers(dp: Dispatcher):
    dp.message.register(process_contact, RegistrationStates.waiting_for_contact)