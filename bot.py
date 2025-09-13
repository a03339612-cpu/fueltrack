import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- Конфигурация ---
# Замените 'YOUR_BOT_TOKEN' на токен вашего бота
# Для безопасности лучше хранить токен в переменной окружения
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN") 

# Замените 'YOUR_WEBAPP_URL' на URL, где будет развернут ваш FastAPI сервер
# Например, 'https://your-app-name.onrender.com'
WEBAPP_URL = os.getenv("WEBAPP_URL", "YOUR_WEBAPP_URL")

# --- Инициализация ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Обработчики команд ---

@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    """
    Этот обработчик будет отправлять приветственное сообщение
    с кнопкой для запуска Web App при команде /start
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🚀 Открыть калькулятор топлива",
        web_app=WebAppInfo(url=WEBAPP_URL)
    )
    
    await message.answer(
        "Добро пожаловать в калькулятор расхода топлива!\n\n"
        "Нажмите на кнопку ниже, чтобы начать.",
        reply_markup=builder.as_markup()
    )


# --- Запуск бота ---
async def main():
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    
    # Проверка наличия токена
    if BOT_TOKEN == "YOUR_BOT_TOKEN":
        logging.critical("Необходимо указать токен бота в переменной BOT_TOKEN.")
        return
        
    if WEBAPP_URL == "YOUR_WEBAPP_URL":
        logging.critical("Необходимо указать URL веб-приложения в переменной WEBAPP_URL.")
        return

    # Запуск polling
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
