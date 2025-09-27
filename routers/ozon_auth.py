from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from datetime import datetime
import os
from cryptography.fernet import Fernet
import httpx
import security

import models
import schemas
import security
import crud
from database import get_db

router = APIRouter(prefix="/ozon_auth", tags=["auth"])

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

@router.post(
    "/", # Путь изменен с "/{client_id}" на "/"
    response_model=schemas.ClientOzonAuth,
    status_code=status.HTTP_201_CREATED,
    summary="Создать или обновить ключи Ozon для текущего пользователя"
)
async def create_or_update_ozon_auth_for_current_user(
    payload: schemas.ClientOzonAuthCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user), # <-- 1. "ОХРАННИК" НА МЕСТЕ
):
    """
    Создает или обновляет ключи Ozon для аутентифицированного пользователя.
    """
    # 2. Находим клиента, который связан с ТЕКУЩИМ пользователем
    result = await db.execute(
        select(models.Client).filter(models.Client.user_id == current_user.id)
    )
    client = result.scalars().first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Связанный клиент для данного пользователя не найден."
        )

    # 2. Валидируем ключи, делая тестовый запрос к Ozon
    await validate_ozon_keys(
        client_id=payload.ozon_client_id, api_key=payload.ozon_api_key
    )

    # 3. Шифруем ключи перед сохранением в базу
    encrypted_client_id_str = security.encrypt_data(payload.ozon_client_id)
    encrypted_api_key_str = security.encrypt_data(payload.ozon_api_key)

    # 4. Ищем, есть ли уже запись с ключами для этого клиента
    auth_entry = await crud.get_ozon_auth_by_client_id(db, client_id=client.id)

    if auth_entry:
        # Если есть, обновляем ее
        auth_entry.encrypted_ozon_client_id = encrypted_client_id_str
        auth_entry.encrypted_ozon_api_key = encrypted_api_key_str
    else:
        # Если нет, создаем новую
        auth_entry = models.ClientOzonAuth(
            client_id=client.id,
            encrypted_ozon_client_id=encrypted_client_id_str,
            encrypted_ozon_api_key=encrypted_api_key_str,
        )
        db.add(auth_entry)

    # 5. Сохраняем изменения в базе
    await db.commit()
    await db.refresh(auth_entry)

    return auth_entry

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
