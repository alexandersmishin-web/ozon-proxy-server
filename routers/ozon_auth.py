from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
import os
from cryptography.fernet import Fernet
import httpx

import models, schemas
from database import get_db

router = APIRouter(prefix="/ozon_auth", tags=["auth"])

# Получение ключа из окружения
try:
    FERNET_SECRET = os.environ['OZON_CRYPT_KEY']
    cipher_suite = Fernet(FERNET_SECRET.encode())
except KeyError:
    # Это вызовет ошибку при запуске, если ключ не установлен
    raise RuntimeError("Переменная окружения OZON_CRYPT_KEY не установлена!")

# --- 2. Новая вспомогательная функция для валидации ключей ---
async def validate_ozon_keys(client_id: str, api_key: str):
    """
    Делает тестовый запрос к Ozon API для проверки валидности ключей.
    Возвращает True в случае успеха, иначе вызывает HTTPException.
    """
    url = "https://api-seller.ozon.ru/v1/warehouse/list"
    headers = {
        "Client-Id": client_id,
        "Api-Key": api_key,
        "Content-Type": "application/json",
    }
    # Пустое тело запроса, так как все параметры опциональны
    payload = {} 

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            
            # Проверяем код ответа. Ozon возвращает 200 при успехе.
            if response.status_code == 200:
                print("Ключи Ozon валидны.")
                return True
            # Ozon возвращает 401, 403 или 404 при неверных ключах
            elif response.status_code in [401, 403, 404]:
                print(f"Ошибка валидации ключей Ozon: {response.status_code}, {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Неверный Client-Id или Api-Key. Пожалуйста, проверьте данные."
                )
            else:
                # Другие возможные ошибки сети или сервера Ozon
                response.raise_for_status()

        except httpx.RequestError as exc:
            # Ошибки сети
            print(f"Сетевая ошибка при попытке валидации ключей Ozon: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Не удалось связаться с сервером Ozon. Попробуйте позже."
            )

@router.post("/{client_id}", response_model=schemas.ClientOzonAuth)
async def create_or_update_auth(client_id: int, payload: schemas.ClientOzonAuthCreate, db: AsyncSession = Depends(get_db)):
    """
    Создает или обновляет ключи Ozon для клиента.
    Если ключи уже существуют, они будут заменены новыми.
    """
    # --- 3. Интеграция валидации ---
    await validate_ozon_keys(
        client_id=payload.ozon_client_id,
        api_key=payload.ozon_api_key
    )    

    # Шифруем полученные ключи
    encrypted_client_id_str = cipher_suite.encrypt(payload.ozon_client_id.encode()).decode()
    encrypted_api_key_str = cipher_suite.encrypt(payload.ozon_api_key.encode()).decode()

    # --- ИСПРАВЛЕНИЕ: Ищем существующую запись ---
    result = await db.execute(
        select(models.ClientOzonAuth).filter(models.ClientOzonAuth.client_id == client_id)
    )
    db_auth = result.scalars().first()

    if db_auth is None:
        # Если записи нет, создаем новую
        print("Creating new auth record...")
        db_auth = models.ClientOzonAuth(
            client_id=client_id,
            encrypted_ozon_client_id=encrypted_client_id_str,
            encrypted_ozon_api_key=encrypted_api_key_str
        )
        db.add(db_auth)
    else:
        # Если запись есть, обновляем ее
        print("Updating existing auth record...")
        db_auth.encrypted_ozon_client_id = encrypted_client_id_str
        db_auth.encrypted_ozon_api_key = encrypted_api_key_str
        # Поле updated_at обновится автоматически благодаря onupdate=datetime.utcnow
    
    await db.commit()
    await db.refresh(db_auth)
    return db_auth

@router.patch("/{auth_id}", response_model=schemas.ClientOzonAuth)
async def update_auth(auth_id: int, payload: schemas.ClientOzonAuthCreate, db: AsyncSession = Depends(get_db)):
    """
    Обновляет существующие ключи Ozon.
    Перед обновлением выполняет проверку ключей на валидность.
    """
    # --- Валидация ---
    await validate_ozon_keys(
        client_id=payload.ozon_client_id,
        api_key=payload.ozon_api_key
    )
    # --- Если валидация прошла успешно ---
    result = await db.execute(select(models.ClientOzonAuth).filter(models.ClientOzonAuth.id == auth_id))
    db_auth = result.scalars().first()
    if not db_auth:
        raise HTTPException(status_code=404, detail="Auth not found")
    db_auth.encrypted_ozon_client_id = cipher_suite.encrypt(payload.ozon_client_id.encode()).decode()
    db_auth.encrypted_ozon_api_key = cipher_suite.encrypt(payload.ozon_api_key.encode()).decode()
    db_auth.updated_at = datetime.utcnow()
    db.add(db_auth)
    await db.commit()
    await db.refresh(db_auth)
    return db_auth

@router.get("/{auth_id}", response_model=schemas.ClientOzonAuth)
async def get_auth(auth_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.ClientOzonAuth).filter(models.ClientOzonAuth.id == auth_id))
    db_auth = result.scalars().first()
    if not db_auth:
        raise HTTPException(status_code=404, detail="Auth not found")
    return db_auth

@router.delete("/{auth_id}", status_code=204)
async def delete_auth(auth_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.ClientOzonAuth).filter(models.ClientOzonAuth.id == auth_id))
    db_auth = result.scalars().first()
    if not db_auth:
        raise HTTPException(status_code=404, detail="Auth not found")
    await db.delete(db_auth)
    await db.commit()
    return None
