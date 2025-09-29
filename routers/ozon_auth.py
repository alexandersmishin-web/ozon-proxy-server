# File: routers/ozon_auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional # Убедитесь, что Optional импортирован
import httpx

import models
import schemas
import security
import crud
from database import get_db

router = APIRouter(prefix="/ozon_auth", tags=["Ozon Auth"])

# --- Ваша превосходная функция валидации остается без изменений ---
async def validate_ozon_keys(client_id: str, api_key: str):
    # ... (ваш код валидации)
    url = "https://api-seller.ozon.ru/v1/warehouse/list"
    headers = {"Client-Id": client_id, "Api-Key": api_key, "Content-Type": "application/json"}
    payload = {} 
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200: return True
            elif response.status_code in [401, 403, 404]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный Client-Id или Api-Key.")
            else: response.raise_for_status()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Не удалось связаться с сервером Ozon.")

# --- УНИВЕРСАЛЬНЫЙ ЭНДПОИНТ ДЛЯ СОЗДАНИЯ КЛЮЧЕЙ ---
@router.post(
    "/",
    response_model=schemas.ClientOzonAuth,
    status_code=status.HTTP_201_CREATED,
    summary="Создать или обновить ключи Ozon"
)
async def create_or_update_ozon_auth(
    payload: schemas.ClientOzonAuthCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    Создает или обновляет ключи Ozon.
    - **Обычный пользователь (клиент):** может обновить только свои ключи. Поле `client_id` в запросе игнорируется.
    - **Суперпользователь (сотрудник):** может обновить ключи для любого клиента, указав `client_id` в запросе.
    """
    target_client: Optional[models.Client] = None

    if current_user.is_superuser:
        # Если это суперпользователь, он ДОЛЖЕН указать, для какого клиента работает
        if payload.client_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Суперпользователь должен указать 'client_id' в теле запроса."
            )
        # Находим клиента по ID из запроса
        target_client = await db.get(models.Client, payload.client_id)
        if not target_client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Клиент с ID {payload.client_id} не найден."
            )
    else:
        # Если это обычный клиент, ищем связанный с ним профиль
        result = await db.execute(
            select(models.Client).filter(models.Client.user_id == current_user.id)
        )
        target_client = result.scalars().first()
        if not target_client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Связанный клиент для данного пользователя не найден."
            )

    # Валидируем ключи
    await validate_ozon_keys(
        client_id=payload.ozon_client_id, api_key=payload.ozon_api_key
    )

    # Шифруем ключи
    encrypted_client_id_str = security.encrypt_data(payload.ozon_client_id)
    encrypted_api_key_str = security.encrypt_data(payload.ozon_api_key)

    # Ищем существующую запись или создаем новую
    auth_entry = await crud.get_ozon_auth_by_client_id(db, client_id=target_client.id)
    if auth_entry:
        auth_entry.encrypted_ozon_client_id = encrypted_client_id_str
        auth_entry.encrypted_ozon_api_key = encrypted_api_key_str
    else:
        auth_entry = models.ClientOzonAuth(
            client_id=target_client.id,
            encrypted_ozon_client_id=encrypted_client_id_str,
            encrypted_ozon_api_key=encrypted_api_key_str,
        )
        db.add(auth_entry)

    # Сохраняем и возвращаем результат
    await db.commit()
    await db.refresh(auth_entry)
    return auth_entry
