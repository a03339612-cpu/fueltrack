import os
import sqlite3
from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
import openpyxl
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter

# --- Настройка базы данных ---
DB_FILE = "fuel_tracker.db"

def init_db():
    if not os.path.exists(DB_FILE):
        print("Creating database...")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('PRAGMA foreign_keys = ON;')
        
        # ИСПРАВЛЕНИЕ: Полная и правильная команда для создания таблицы users
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT UNIQUE NOT NULL
        )''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            plate TEXT,
            current_mileage REAL DEFAULT 0,
            current_fuel REAL DEFAULT 0,
            consumption_driving REAL DEFAULT 8.0,
            consumption_idle REAL DEFAULT 1.0,
            is_active BOOLEAN DEFAULT 1
        )''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS fuel_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_id INTEGER NOT NULL,
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
            final_fuel_level REAL NOT NULL,
            FOREIGN KEY (car_id) REFERENCES cars (id) ON DELETE CASCADE
        )''')
        
        conn.commit()
        conn.close()
        print("Database created successfully.")

# --- Модели данных (Pydantic) ---
class CarBase(BaseModel):
    name: str
    plate: Optional[str] = None

class CarCreate(CarBase):
    user_id: str

class CarDetailsUpdate(CarBase):
    pass

class CarUpdate(BaseModel):
    current_mileage: float = Field(..., gt=0)
    current_fuel: float = Field(..., ge=0)
    consumption_driving: float = Field(..., gt=0)
    consumption_idle: float = Field(..., gt=0)

class Car(CarBase):
    id: int
    user_id: str
    current_mileage: float
    current_fuel: float
    consumption_driving: float
    consumption_idle: float
    is_active: bool

class LogCreate(BaseModel):
    car_id: int; user_id: str; date: date; start_mileage: float; end_mileage: float; refueled: float; idle_hours: float; consumption_driving: float; consumption_idle: float; start_fuel: float

class LogEntryResponse(BaseModel):
    date: date; trip_distance: float; refueled: float; fuel_consumed_total: float; final_fuel_level: float

class InitData(BaseModel):
    cars: List[Car]; active_car_id: Optional[int]


# --- Инициализация FastAPI и БД ---
init_db()
app = FastAPI()

def get_db_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- API эндпоинты ---
@app.get("/api/init/{user_id}", response_model=InitData)
def get_initial_data(user_id: str):
    conn = get_db_conn(); cursor = conn.cursor(); cursor.execute("SELECT * FROM cars WHERE user_id = ?", (user_id,)); cars_data = cursor.fetchall(); cars = [dict(row) for row in cars_data]; active_car = next((car for car in cars if car['is_active']), None); active_car_id = active_car['id'] if active_car else None
    if not active_car_id and cars:
        active_car_id = cars[0]['id']; cursor.execute("UPDATE cars SET is_active = 1 WHERE id = ?", (active_car_id,)); conn.commit()
    conn.close(); return {"cars": cars, "active_car_id": active_car_id}

@app.post("/api/cars", response_model=Car)
def add_car(car: CarCreate):
    conn = get_db_conn(); cursor = conn.cursor(); cursor.execute("UPDATE cars SET is_active = 0 WHERE user_id = ?", (car.user_id,)); cursor.execute("INSERT INTO cars (user_id, name, plate, is_active) VALUES (?, ?, ?, 1)", (car.user_id, car.name, car.plate)); new_car_id = cursor.lastrowid; conn.commit()
    cursor.execute("SELECT * FROM cars WHERE id = ?", (new_car_id,)); new_car = dict(cursor.fetchone()); conn.close(); return new_car

@app.put("/api/cars/details/{car_id}", response_model=CarDetailsUpdate)
def update_car_details(car_id: int, details: CarDetailsUpdate):
    conn = get_db_conn(); cursor = conn.cursor(); cursor.execute("UPDATE cars SET name = ?, plate = ? WHERE id = ?", (details.name, details.plate, car_id)); conn.commit(); conn.close(); return details

@app.put("/api/cars/settings/{car_id}", response_model=CarUpdate)
def update_car_settings(car_id: int, settings: CarUpdate):
    conn = get_db_conn(); cursor = conn.cursor()
    cursor.execute("UPDATE cars SET current_mileage = ?, current_fuel = ?, consumption_driving = ?, consumption_idle = ? WHERE id = ?", (settings.current_mileage, settings.current_fuel, settings.consumption_driving, settings.consumption_idle, car_id))
    conn.commit(); conn.close(); return settings

@app.put("/api/cars/activate/{car_id}/{user_id}")
def set_active_car(car_id: int, user_id: str):
    conn = get_db_conn(); cursor = conn.cursor(); cursor.execute("UPDATE cars SET is_active = 0 WHERE user_id = ?", (user_id,)); cursor.execute("UPDATE cars SET is_active = 1 WHERE id = ? AND user_id = ?", (car_id, user_id)); conn.commit(); conn.close(); return {"message": "Active car updated"}

@app.delete("/api/cars/{car_id}/{user_id}")
def delete_car(car_id: int, user_id: str):
    conn = get_db_conn(); cursor = conn.cursor(); cursor.execute('PRAGMA foreign_keys = ON;')
    cursor.execute("DELETE FROM cars WHERE id = ? AND user_id = ?", (car_id, user_id)); conn.commit()
    cursor.execute("SELECT id FROM cars WHERE user_id = ? LIMIT 1", (user_id,)); remaining_car = cursor.fetchone()
    if remaining_car:
        cursor.execute("UPDATE cars SET is_active = 1 WHERE id = ?", (remaining_car['id'],)); conn.commit()
    conn.close(); return {"message": "Car deleted successfully"}

@app.get("/api/logs/{car_id}", response_model=List[LogEntryResponse])
def get_car_logs(car_id: int):
    conn = get_db_conn(); cursor = conn.cursor(); cursor.execute("SELECT date, trip_distance, refueled, fuel_consumed_total, final_fuel_level FROM fuel_logs WHERE car_id = ? ORDER BY date DESC, id DESC LIMIT 5", (car_id,)); logs = [dict(row) for row in cursor.fetchall()]; conn.close(); return logs

@app.post("/api/logs")
def calculate_and_log_trip(log: LogCreate):
    trip_distance = log.end_mileage - log.start_mileage; fuel_consumed_driving = (trip_distance / 100) * log.consumption_driving; fuel_consumed_idle = log.idle_hours * log.consumption_idle; fuel_consumed_total = fuel_consumed_driving + fuel_consumed_idle; fuel_after_trip = log.start_fuel - fuel_consumed_total; final_fuel_level = fuel_after_trip + log.refueled
    if final_fuel_level < 0: raise HTTPException(status_code=400, detail="Расчетный остаток топлива отрицательный.")
    conn = get_db_conn(); cursor = conn.cursor(); cursor.execute("INSERT INTO fuel_logs (car_id, date, start_mileage, end_mileage, trip_distance, refueled, idle_hours, fuel_consumed_driving, fuel_consumed_idle, fuel_consumed_total, fuel_after_trip, final_fuel_level) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (log.car_id, log.date, log.start_mileage, log.end_mileage, trip_distance, log.refueled, log.idle_hours, fuel_consumed_driving, fuel_consumed_idle, fuel_consumed_total, fuel_after_trip, final_fuel_level)); cursor.execute("UPDATE cars SET current_mileage = ?, current_fuel = ? WHERE id = ?", (log.end_mileage, final_fuel_level, log.car_id)); conn.commit(); conn.close(); return {"new_mileage": log.end_mileage, "new_fuel_level": final_fuel_level}

@app.get("/api/report")
def generate_report(car_id: int, start_date: date, end_date: date):
    conn = get_db_conn(); cursor = conn.cursor(); cursor.execute("SELECT name, plate FROM cars WHERE id = ?", (car_id,)); car_info = cursor.fetchone()
    if not car_info: raise HTTPException(status_code=404, detail="Car not found")
    query = "SELECT date, start_mileage, end_mileage, trip_distance, refueled, idle_hours, fuel_consumed_total, final_fuel_level FROM fuel_logs WHERE car_id = ? AND date BETWEEN ? AND ? ORDER BY date ASC"; cursor.execute(query, (car_id, start_date, end_date)); logs = cursor.fetchall(); conn.close()
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Отчет по топливу"; ws.merge_cells('A1:H1'); title_cell = ws['A1']; title_cell.value = f"Отчет по автомобилю {car_info['name']} ({car_info['plate']}) за период с {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')}"; title_cell.font = Font(bold=True, size=14); title_cell.alignment = Alignment(horizontal='center'); headers = ["Дата", "Пробег нач.", "Пробег кон.", "Пробег за поездку", "Заправлено, л", "Простой, ч", "Расход, л", "Остаток, л"]; ws.append(headers)
    for cell in ws[2]: cell.font = Font(bold=True)
    for log in logs: ws.append(list(log))
    for column_cells in ws.columns:
        max_length = 0; column = get_column_letter(column_cells[0].column)
        for cell in column_cells:
            try:
                if len(str(cell.value)) > max_length: max_length = len(str(cell.value))
            except: pass
        ws.column_dimensions[column].width = (max_length + 2)
    from io import BytesIO; virtual_workbook = BytesIO(); wb.save(virtual_workbook); virtual_workbook.seek(0)
    return Response(content=virtual_workbook.read(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename=report_{car_id}_{start_date}_to_{end_date}.xlsx"})

app.mount("/", StaticFiles(directory=".", html=True), name="static")

