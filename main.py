import os
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import IntegrityError
import datetime
import io
import openpyxl

# --- Конфигурация базы данных ---
DATABASE_URL = "sqlite:///./fuel_tracker.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Модели SQLAlchemy (Структура таблиц БД) ---
class Car(Base):
    __tablename__ = "cars"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    name = Column(String, index=True)
    plate = Column(String, nullable=True)
    
    # Текущие значения, обновляемые после каждого расчета
    current_mileage = Column(Float, default=0.0)
    current_fuel = Column(Float, default=0.0)
    
    # Настройки по умолчанию
    consumption_driving = Column(Float, default=8.0) # л/100км
    consumption_idle = Column(Float, default=1.0) # л/час


class FuelLog(Base):
    __tablename__ = "fuel_logs"
    id = Column(Integer, primary_key=True, index=True)
    car_id = Column(Integer, ForeignKey("cars.id"))
    user_id = Column(String)
    date = Column(Date)
    
    start_mileage = Column(Float)
    end_mileage = Column(Float)
    
    refueled = Column(Float)
    idle_hours = Column(Float)
    
    consumption_driving = Column(Float) # сохраненный на момент расчета
    consumption_idle = Column(Float) # сохраненный на момент расчета
    
    calculated_fuel_after = Column(Float)


# Создаем таблицы в БД при запуске
Base.metadata.create_all(bind=engine)

# --- Pydantic модели (для валидации данных API) ---
class CarBase(BaseModel):
    name: str
    plate: Optional[str] = None
    
class CarCreate(CarBase):
    user_id: str

class CarUpdate(BaseModel):
    current_mileage: Optional[float] = None
    current_fuel: Optional[float] = None
    consumption_driving: Optional[float] = None
    consumption_idle: Optional[float] = None

class CarResponse(CarBase):
    id: int
    user_id: str
    current_mileage: float
    current_fuel: float
    consumption_driving: float
    consumption_idle: float
    
    class Config:
        from_attributes = True

class LogCreate(BaseModel):
    car_id: int
    user_id: str
    end_mileage: float
    refueled: float
    idle_hours: float
    date: datetime.date
    start_mileage: float
    start_fuel: float
    consumption_driving: float
    consumption_idle: float

class LogResponse(BaseModel):
    id: int
    date: datetime.date
    start_mileage: float
    end_mileage: float
    refueled: float
    idle_hours: float
    calculated_fuel_after: float

    class Config:
        from_attributes = True

class InitDataResponse(BaseModel):
    cars: List[CarResponse]
    active_car_id: Optional[int] = None

class CalculationResult(BaseModel):
    new_mileage: float
    new_fuel_level: float


# --- FastAPI приложение ---
app = FastAPI(title="Fuel Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Для простоты разработки, в продакшене лучше указать конкретный домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Функция для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- API эндпоинты ---

@app.get("/", include_in_schema=False)
async def read_root():
    """Отдает главный HTML файл приложения."""
    return FileResponse('index.html')

@app.get("/api/init/{user_id}", response_model=InitDataResponse)
def get_initial_data(user_id: str, db: Session = Depends(get_db)):
    """Получение начальных данных для пользователя: список его машин и активная машина."""
    cars = db.query(Car).filter(Car.user_id == user_id).all()
    if not cars:
        return {"cars": [], "active_car_id": None}
    
    # По умолчанию активной делаем первую машину
    active_car_id = cars[0].id
    return {"cars": cars, "active_car_id": active_car_id}

@app.post("/api/cars", response_model=CarResponse)
def create_car(car_data: CarCreate, db: Session = Depends(get_db)):
    """Добавление нового автомобиля."""
    db_car = Car(**car_data.model_dump())
    db.add(db_car)
    db.commit()
    db.refresh(db_car)
    return db_car

@app.get("/api/cars/{user_id}", response_model=List[CarResponse])
def get_user_cars(user_id: str, db: Session = Depends(get_db)):
    """Получение списка автомобилей пользователя."""
    return db.query(Car).filter(Car.user_id == user_id).all()

@app.put("/api/cars/{car_id}", response_model=CarResponse)
def update_car_settings(car_id: int, settings: CarUpdate, db: Session = Depends(get_db)):
    """Обновление настроек автомобиля (включая начальный пробег/топливо)."""
    db_car = db.query(Car).filter(Car.id == car_id).first()
    if not db_car:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")

    update_data = settings.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_car, key, value)
    
    db.commit()
    db.refresh(db_car)
    return db_car


@app.post("/api/logs", response_model=CalculationResult)
def create_fuel_log(log_data: LogCreate, db: Session = Depends(get_db)):
    """Создание записи о поездке и расчет остатка."""
    car = db.query(Car).filter(Car.id == log_data.car_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")
    
    # Логика расчета
    distance = log_data.end_mileage - log_data.start_mileage
    if distance < 0:
        raise HTTPException(status_code=400, detail="Конечный пробег не может быть меньше начального")

    consumption_on_trip = distance * (log_data.consumption_driving / 100)
    consumption_on_idle = log_data.idle_hours * log_data.consumption_idle
    total_consumption = consumption_on_trip + consumption_on_idle
    
    final_fuel = (log_data.start_fuel + log_data.refueled) - total_consumption
    if final_fuel < 0:
        final_fuel = 0 # Не может быть отрицательным
    
    # Создаем запись в логе
    db_log = FuelLog(
        car_id=log_data.car_id,
        user_id=log_data.user_id,
        date=log_data.date,
        start_mileage=log_data.start_mileage,
        end_mileage=log_data.end_mileage,
        refueled=log_data.refueled,
        idle_hours=log_data.idle_hours,
        consumption_driving=log_data.consumption_driving,
        consumption_idle=log_data.consumption_idle,
        calculated_fuel_after=final_fuel
    )
    db.add(db_log)
    
    # Обновляем текущие данные автомобиля
    car.current_mileage = log_data.end_mileage
    car.current_fuel = final_fuel
    
    db.commit()
    
    return CalculationResult(new_mileage=car.current_mileage, new_fuel_level=car.current_fuel)


@app.get("/api/report")
def get_excel_report(car_id: int, month: str = Query(..., pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db)):
    """Генерация и отдача Excel отчета за выбранный месяц."""
    try:
        year, month_num = map(int, month.split('-'))
        start_date = datetime.date(year, month_num, 1)
        end_date = (start_date + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат месяца. Используйте YYYY-MM.")

    logs = db.query(FuelLog).filter(
        FuelLog.car_id == car_id,
        FuelLog.date >= start_date,
        FuelLog.date <= end_date
    ).order_by(FuelLog.date).all()
    
    if not logs:
        raise HTTPException(status_code=404, detail="Нет данных за указанный период")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Отчет за {month}"
    
    headers = [
        "Дата", "Нач. пробег", "Кон. пробег", "Пробег за поездку", "Заправлено (л)", 
        "Простой (ч)", "Расход (движ.)", "Расход (простой)", "Остаток (л)"
    ]
    ws.append(headers)
    
    for log in logs:
        trip_distance = log.end_mileage - log.start_mileage
        row = [
            log.date.strftime("%Y-%m-%d"),
            log.start_mileage,
            log.end_mileage,
            trip_distance,
            log.refueled,
            log.idle_hours,
            log.consumption_driving,
            log.consumption_idle,
            log.calculated_fuel_after
        ]
        ws.append(row)
        
    # Сохраняем файл в памяти
    virtual_workbook = io.BytesIO()
    wb.save(virtual_workbook)
    virtual_workbook.seek(0)
    
    return StreamingResponse(
        virtual_workbook,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=report_{car_id}_{month}.xlsx"}
    )

# Для запуска через `python main.py`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
