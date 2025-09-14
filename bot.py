import asyncio
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton

# --- Получаем переменные окружения ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEB_APP_URL = os.getenv("WEB_APP_URL")

# Проверка наличия переменных
if not BOT_TOKEN:
    sys.exit("Ошибка: BOT_TOKEN не найден в переменных окружения!")
if not WEB_APP_URL:
     sys.exit("Ошибка: WEB_APP_URL не найден в переменных окружения!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    """Отправляет приветственное сообщение с кнопкой Web App."""
    web_app_info = WebAppInfo(url=WEB_APP_URL)
    keyboard = [
        [KeyboardButton(text="Нажмите на кнопку", web_app=web_app_info)]
    ]
    markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    await message.answer(
        "Добро пожаловать в калькулятор топлива!",
        reply_markup=markup
    )

async def main() -> None:
    print("Запуск бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")

