import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardRemove
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

# Инициализируем бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Сообщение о технических работах
MAINTENANCE_MESSAGE = """
🔧 *Бот временно не работает*

В настоящее время проводятся технические работы. 
Приносим извинения за временные неудобства.

⏰ *Примерное время восстановления:* 
уточняется

📞 *По всем вопросам обращайтесь к администраторам.*

Бот автоматически уведомит вас, когда работа будет восстановлена.
"""


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        MAINTENANCE_MESSAGE,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(Command("book"))
async def cmd_book(message: types.Message):
    await message.answer(
        MAINTENANCE_MESSAGE,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        MAINTENANCE_MESSAGE,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )



# Обработчик всех callback запросов
@dp.callback_query()
async def any_callback(callback: types.CallbackQuery):
    await callback.message.answer(
        MAINTENANCE_MESSAGE,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    await callback.answer()

async def main():
    """Основная функция запуска бота в режиме техобслуживания"""
    try:
        logger.info("Запуск бота в режиме технического обслуживания...")

        logger.info("Бот готов к работе в режиме технического обслуживания")
        logger.info("Бот отвечает на все сообщения уведомлением о техработах")

        # Запускаем поллинг
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    print("=" * 50)
    print("РЕЖИМ ТЕХНИЧЕСКОГО ОБСЛУЖИВАНИЯ")
    print("Бот будет отвечать на все сообщения уведомлением о техработах")
    print("=" * 50)

    asyncio.run(main())