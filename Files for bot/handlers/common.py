from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery
from database import Database
from keyboards import get_main_menu_keyboard, get_cancel_booking_keyboard
from helpers import format_date_display

db = Database()

async def view_my_bookings(callback: CallbackQuery):
    """Показывает активные бронирования пользователя"""
    await db.cleanup_expired_bookings()  # Очищаем просроченные брони
    bookings = await db.get_user_bookings(callback.from_user.id, active_only=True)

    if not bookings:
        await callback.message.answer("📭 У вас нет активных бронирований.")
        await callback.answer()
        return

    response = "📋 Ваши активные бронирования:\n\n"
    for booking in bookings:
        display_date = format_date_display(booking['booking_date'])
        response += (
            f"🎯 {booking['booking_type']}\n"
            f"📅 {display_date}\n"
            f"🕒 {booking['start_time']} - {booking['end_time']}\n"
            f"🔢 ID: {booking['id']}\n"
            f"---\n"
        )

    await callback.message.answer(response)
    await callback.answer()

async def start_cancel_booking(callback: CallbackQuery):
    """Начинает процесс отмены бронирования"""
    await db.cleanup_expired_bookings()  # Очищаем просроченные брони
    bookings = await db.get_user_bookings(callback.from_user.id, active_only=True)

    if not bookings:
        await callback.message.answer("📭 У вас нет активных бронирований для отмены.")
        await callback.answer()
        return

    await callback.message.answer(
        "❌ Выберите бронирование для отмены:",
        reply_markup=get_cancel_booking_keyboard(bookings)
    )
    await callback.answer()

async def cancel_specific_booking(callback: CallbackQuery):
    """Отменяет конкретное бронирование"""
    booking_id = int(callback.data.split('_')[1])

    success = await db.cancel_booking(booking_id, callback.from_user.id)

    if success:
        await callback.message.answer("✅ Бронирование успешно отменено!")
        await callback.message.answer(
            "🏠 Главное меню:",
            reply_markup=get_main_menu_keyboard(callback.from_user.id)
        )
    else:
        await callback.message.answer(
            "❌ Не удалось отменить бронирование. Возможно, оно уже отменено или не существует.")

    await callback.answer()

def register_common_handlers(dp: Dispatcher):
    dp.callback_query.register(view_my_bookings, F.data == "view_my_bookings")
    dp.callback_query.register(start_cancel_booking, F.data == "cancel_booking")
    dp.callback_query.register(cancel_specific_booking, F.data.startswith("cancel_"))