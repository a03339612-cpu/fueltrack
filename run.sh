#!/bin/bash

# Устанавливаем зависимости
pip install -r requirements.txt

# Запускаем веб-сервер в фоновом режиме (&)
uvicorn main:app --host 0.0.0.0 --port 10000 &

# Запускаем бота
python bot.py
