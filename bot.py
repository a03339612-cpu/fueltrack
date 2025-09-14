import asyncio
import os
import sys
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton

# Код должен брать переменные ТОЛЬКО из окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEB_APP_URL = os.getenv("WEB_APP_URL")

# Проверки, что переменные были найдены в настройках Render
if not BOT_TOKEN:
    sys.exit("Ошибка: BOT_TOKEN не найден в переменных окружения!")
if not WEB_APP_URL:
    sys.exit("Ошибка: WEB_APP_URL не найден в переменных окружения!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    web_app_button = KeyboardButton(
        text="Открыть калькулятор топлива",
        web_app=WebAppInfo(url=WEB_APP_URL)
    )
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[web_app_button]],
        resize_keyboard=True
    )
    await message.answer(
        "Добро пожаловать в калькулятор топлива! Нажмите на кнопку ниже, чтобы начать.",
        reply_markup=keyboard
    )

async def main():
    print("Бот запускается через 5 секунд...")
    # Добавляем небольшую задержку, чтобы веб-сервер точно успел стартовать
    time.sleep(5)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        print("Запуск бота...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен вручную.")

