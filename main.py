import asyncio
import logging
import sys
from aiogram.types import Message
from aiogram.filters import Command
from config import dp, bot
from database import Database
from handlers import register_all_handlers
from keyboards import get_main_menu_keyboard


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def cmd_start(message: Message):
    """Команда для начала работы"""
    try:
        await message.answer(
            "🏠 Главное меню:",
            reply_markup=get_main_menu_keyboard(message.from_user.id)
        )
    except Exception as e:
        logger.error(f"Error in cmd_start: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

async def cmd_help(message: Message):
    """Команда помощи"""
    help_text = """
🤖 *Доступные команды:*

/start - Начать работу с ботом
/help - Показать эту справку
/book - Начать бронирование

📋 *Основные функции:*
• Бронирование (Лекторий, Playstation, Компьютеры)
• Просмотр своих бронирований
• Отмена бронирований
• Просмотр бронирований по неделям

⏰ *Часы работы коворкинга:*
Пн-Чт: 18:00 - 23:00
Пт: 17:00 - 23:00
Сб: 14:00 - 19:00
Вс: выходной

💻 *Компьютеры:* доступно 16 мест

📞 *По вопросам обращайтесь к администраторам.*
    """
    await message.answer(help_text, parse_mode="Markdown")

async def cleanup_task():
    """Фоновая задача для очистки просроченных бронирований"""
    try:
        db = Database()
        await db.create_pool()
        while True:
            try:
                await db.cleanup_expired_bookings()
                logger.info("Expired bookings cleanup completed")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
            await asyncio.sleep(3600)
    except Exception as e:
        logger.error(f"Failed to start cleanup task: {e}")

async def main():
    """Основная функция запуска бота"""
    try:
        logger.info("Бот запускается...")

        # Инициализация базы данных
        db = Database()
        await db.create_pool()
        logger.info("База данных инициализирована")

        # Регистрация обработчиков
        register_all_handlers(dp)

        # Регистрация команд
        dp.message.register(cmd_start, Command("start"))
        dp.message.register(cmd_start, Command("book"))
        dp.message.register(cmd_help, Command("help"))

        # Очистка просроченных бронирований при запуске
        await db.cleanup_expired_bookings()

        # Запуск фоновой задачи
        asyncio.create_task(cleanup_task())

        logger.info("Бот успешно запущен!")

        # Запуск поллинга
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        sys.exit(1)
    finally:
        logger.info("Бот остановлен.")

if __name__ == "__main__":
    asyncio.run(main())