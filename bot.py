import asyncio
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton

# --- ВАЖНОЕ ИЗМЕНЕНИЕ: Проверка переменных окружения ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "8422469676:AAFhfdZsr4m0RD6FaHijswQQSG0BKn7x2-g")
WEB_APP_URL = os.getenv("WEBAPP_URL", "https://fueltrack-7puj.onrender.com")

if not BOT_TOKEN:
    # Если токен не найден, выводим ошибку и завершаем работу
    sys.exit("Ошибка: BOT_TOKEN не найден в переменных окружения!")

if not WEB_APP_URL:
    # Если URL не найден, выводим ошибку и завершаем работу
    sys.exit("Ошибка: WEB_APP_URL не найден в переменных окружения!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    """
    Этот обработчик вызывается, когда пользователь отправляет команду /start
    """
    # Создаем кнопку, которая открывает веб-приложение
    web_app_button = KeyboardButton(
        text="Открыть калькулятор топлива",
        web_app=WebAppInfo(url=WEB_APP_URL)
    )
    
    # Создаем клавиатуру с одной этой кнопкой
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[web_app_button]],
        resize_keyboard=True
    )
    
    await message.answer(
        "Добро пожаловать в калькулятор топлива! Нажмите на кнопку ниже, чтобы начать.",
        reply_markup=keyboard
    )

async def main():
    """
    Главная функция для запуска бота
    """
    print("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен вручную.")



