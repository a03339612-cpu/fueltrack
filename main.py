import os
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
import openpyxl
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter

# --- НАСТРОЙКА ---
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

# --- ФУНКЦИИ БАЗЫ ДАННЫХ ---
def get_db_conn():
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL не настроен на сервере!")
    # ИЗМЕНЕНИЕ: Добавляем sslmode=require для Supabase
    # Эта строка теперь автоматически добавляет нужный параметр, если его нет
    conn_str = DATABASE_URL
    if 'sslmode' not in conn_str:
        conn_str = f"{conn_str}?sslmode=require"
    return psycopg2.connect(conn_str)

def init_db():
    print("Проверка и инициализация таблиц базы данных...")
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            # ... (код создания таблиц без изменений) ...
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS cars (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                plate TEXT,
                current_mileage REAL DEFAULT 0,
                current_fuel REAL DEFAULT 0,
                consumption_driving REAL DEFAULT 8.0,
                consumption_idle REAL DEFAULT 1.0,
                is_active BOOLEAN DEFAULT true
            )''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS fuel_logs (
                id SERIAL PRIMARY KEY,
                car_id INTEGER NOT NULL REFERENCES cars(id) ON DELETE CASCADE,
                date DATE NOT NULL,
                start_mileage REAL NOT NULL,
                end_mileage REAL NOT NULL,
                trip_distance REAL NOT NULL,
                refueled REAL DEFAULT 0,
                idle_hours REAL DEFAULT 0,
                fuel_consumed_driving REAL NOT NULL,
                fuel_consumed_idle REAL NOT NULL,
                fuel_consumed_total REAL NOT NULL,
                fuel_after_trip REAL NOT NULL,
                final_fuel_level REAL NOT NULL
            )''')
            conn.commit()
        conn.close()
        print("База данных готова к работе.")
    except Exception as e:
        print(f"!!! ОШИБКА ИНИЦИАЛИЗАЦИИ БАЗЫ ДАННЫХ: {e}")

# --- СОБЫТИЕ ЗАПУСКА ПРИЛОЖЕНИЯ ---
@app.on_event("startup")
async def startup_event():
    init_db()

# ... (остальной код FastAPI без изменений) ...

# --- Модели данных (Pydantic) ---
class CarBase(BaseModel): name: str; plate: Optional[str] = None
class CarCreate(CarBase): user_id: str
# ... (и так далее)

# --- API эндпоинты ---
@app.get("/api/init/{user_id}", response_model=InitData)
def get_initial_data(user_id: str):
    # ...
# ... (и так далее)

app.mount("/", StaticFiles(directory=".", html=True), name="static")



