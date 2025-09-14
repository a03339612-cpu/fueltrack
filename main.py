import os
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
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
    """ Устанавливает соединение с базой данных. """
    if not DATABASE_URL:
        raise RuntimeError("Критическая ошибка: переменная DATABASE_URL не установлена на сервере!")
    
    conn_str = DATABASE_URL
    if 'sslmode' not in conn_str:
        conn_str = f"{conn_str}?sslmode=require"
        
    try:
        print("Попытка подключения к базе данных...")
        conn = psycopg2.connect(conn_str)
        print("Подключение к базе данных успешно!")
        return conn
    except psycopg2.OperationalError as e:
        # Эта ошибка будет видна в логах Render, если URL неправильный
        raise RuntimeError(f"Критическая ошибка: не удалось подключиться к базе данных. Проверьте правильность DATABASE_URL. Детали: {e}")

def init_db():
    """ Создает таблицы в базе, если их еще нет. """
    print("Проверка и инициализация таблиц базы данных...")
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS cars (
                id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, name TEXT NOT NULL, plate TEXT,
                current_mileage REAL DEFAULT 0, current_fuel REAL DEFAULT 0,
                consumption_driving REAL DEFAULT 8.0, consumption_idle REAL DEFAULT 1.0,
                is_active BOOLEAN DEFAULT true
            )''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS fuel_logs (
                id SERIAL PRIMARY KEY, car_id INTEGER NOT NULL REFERENCES cars(id) ON DELETE CASCADE,
                date DATE NOT NULL, start_mileage REAL NOT NULL, end_mileage REAL NOT NULL,
                trip_distance REAL NOT NULL, refueled REAL DEFAULT 0, idle_hours REAL DEFAULT 0,
                fuel_consumed_driving REAL NOT NULL, fuel_consumed_idle REAL NOT NULL,
                fuel_consumed_total REAL NOT NULL, fuel_after_trip REAL NOT NULL,
                final_fuel_level REAL NOT NULL
            )''')
            conn.commit()
        conn.close()
        print("База данных готова к работе.")
    except Exception as e:
        print(f"!!! ОШИБКА ИНИЦИАЛИЗАЦИИ БАЗЫ ДАННЫХ: {e}")
        raise e

# --- СОБЫТИЕ ЗАПУСКА ПРИЛОЖЕНИЯ ---
@app.on_event("startup")
async def startup_event():
    init_db()

# --- Модели данных и эндпоинты (без изменений) ---
class CarBase(BaseModel): name: str; plate: Optional[str] = None
class CarCreate(CarBase): user_id: str
class CarDetailsUpdate(CarBase): pass
class CarUpdate(BaseModel): current_mileage: float; current_fuel: float; consumption_driving: float; consumption_idle: float
class Car(CarBase): id: int; user_id: str; current_mileage: float; current_fuel: float; consumption_driving: float; consumption_idle: float; is_active: bool
class LogCreate(BaseModel): car_id: int; user_id: str; date: date; start_mileage: float; end_mileage: float; refueled: float; idle_hours: float; consumption_driving: float; consumption_idle: float; start_fuel: float
class LogEntryResponse(BaseModel): date: date; trip_distance: float; refueled: float; fuel_consumed_total: float; final_fuel_level: float
class InitData(BaseModel): cars: List[Car]; active_car_id: Optional[int]

@app.get("/api/init/{user_id}", response_model=InitData)
def get_initial_data(user_id: str):
    conn = get_db_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT * FROM cars WHERE user_id = %s", (user_id,))
        cars = cursor.fetchall()
        active_car = next((car for car in cars if car['is_active']), None)
        active_car_id = active_car['id'] if active_car else None
        if not active_car_id and cars:
            active_car_id = cars[0]['id']
            cursor.execute("UPDATE cars SET is_active = true WHERE id = %s", (active_car_id,))
            conn.commit()
    conn.close()
    return {"cars": cars, "active_car_id": active_car_id}
# ... (остальные эндпоинты, скопируйте из предыдущих версий, они не менялись)
# ...
app.mount("/", StaticFiles(directory=".", html=True), name="static")




