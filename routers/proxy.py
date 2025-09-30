# In: routers/proxy.py

from fastapi import (
    APIRouter, Request, Depends, HTTPException, 
    status, Response, Body, Header # 1. Убедитесь, что Header импортирован
)
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from cryptography.fernet import InvalidToken
import httpx

import models
import schemas
import crud
from database import get_db
import security

router = APIRouter(prefix="/proxy", tags=["Proxy"])

# =============================================================================
# ОБЩАЯ "РАБОЧАЯ" ФУНКЦИЯ (САМАЯ ФИНАЛЬНАЯ ВЕРСИЯ)
# =============================================================================
async def _common_proxy_logic(
    request: Request,
    db: AsyncSession,
    current_user: models.User,
    ozon_path: str,
    x_target_client_id: int,
):
    # Проверка роли суперпользователя (остается без изменений)
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещен.")

    # Проверка прав доступа (остается без изменений)
    has_permission = await crud.check_client_permission(db=db, client_id=x_target_client_id, permission_name=ozon_path)
    if not has_permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"У клиента (ID: {x_target_client_id}) нет разрешения на вызов метода '{ozon_path}'")

    # --- ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ ЗДЕСЬ ---
    # Заменяем прямой вызов к базе на нашу новую, надежную CRUD-функцию
    target_client = await crud.get_client(db, client_id=x_target_client_id)

    # Проверка наличия клиента и его ключей (остается без изменений)
    if not target_client or not target_client.ozon_auth:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Клиент с ID {x_target_client_id} или его ключи Ozon не найдены.")

    # Расшифровка ключей (остается без изменений)
    try:
        # Пытаемся расшифровать Client-Id
        decrypted_client_id = security.decrypt_data(target_client.ozon_auth.encrypted_ozon_client_id)
    except InvalidToken:
        # Если токен невалиден, показываем его
        failed_value = target_client.ozon_auth.encrypted_ozon_client_id
        raise HTTPException(
            status_code=500,
            detail=f"Не удалось расшифровать Client-Id. Ключ шифрования не подходит. Проблемное значение в базе: '{failed_value}'"
        )
    except Exception as e:
        # Ловим другие ошибки, например, если поле было None
        raise HTTPException(status_code=500, detail=f"Неожиданная ошибка при расшифровке Client-Id: {e}")

    try:
        # Пытаемся расшифровать Api-Key
        decrypted_api_key = security.decrypt_data(target_client.ozon_auth.encrypted_ozon_api_key)
    except InvalidToken:
        # Если токен невалиден, показываем его
        failed_value = target_client.ozon_auth.encrypted_ozon_api_key
        raise HTTPException(
            status_code=500,
            detail=f"Не удалось расшифровать Api-Key. Ключ шифрования не подходит. Проблемное значение в базе: '{failed_value}'"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Неожиданная ошибка при расшифровке Api-Key: {e}")

    # Пересылка запроса в Ozon (весь остальной код функции остается без изменений)
    ozon_api_url = f"https://api-seller.ozon.ru/{ozon_path}"
    headers_to_forward = {
        "Client-Id": decrypted_client_id,
        "Api-Key": decrypted_api_key,
        "Content-Type": request.headers.get("content-type", "application/json"),
    }
    
    body_bytes = await request.body()

    async with httpx.AsyncClient() as ozon_client:
        try:
            req = ozon_client.build_request(
                method=request.method,
                url=ozon_api_url,
                headers=headers_to_forward,
                params=request.query_params,
                content=body_bytes,
                timeout=30.0,
            )
            response = await ozon_client.send(req)
        except httpx.RequestError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Ошибка соединения с Ozon API: {exc}")

    return Response(content=response.content, status_code=response.status_code, headers=dict(response.headers))

# =============================================================================
# "ТОНКИЕ" ЭНДПОИНТЫ (С ВОЗВРАЩЕННЫМИ `Header` и `Body`)
# =============================================================================

@router.post("/{ozon_path:path}", summary="Проксирование POST запросов")
async def proxy_post(
    ozon_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
    # 3. ВОЗВРАЩАЕМ ЯВНОЕ ОБЪЯВЛЕНИЕ ПАРАМЕТРОВ ДЛЯ SWAGGER
    body: Any = Body(None, description="Тело запроса в формате JSON"),
    x_target_client_id: int = Header(..., alias="X-Target-Client-ID", description="ID целевого клиента")
):
    return await _common_proxy_logic(request, db, current_user, ozon_path, x_target_client_id)

@router.get("/{ozon_path:path}", summary="Проксирование GET запросов")
async def proxy_get(
    ozon_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
    # Для GET-запросов тело не нужно, только заголовок
    x_target_client_id: int = Header(..., alias="X-Target-Client-ID", description="ID целевого клиента")
):
    return await _common_proxy_logic(request, db, current_user, ozon_path, x_target_client_id)

# 4. Аналогично обновите PUT, PATCH и DELETE, добавив в их сигнатуры `x_target_client_id: int = Header(...)`
# и `body: Any = Body(...)` для PUT и PATCH.


# 4. АНАЛОГИЧНО ОБНОВИТЕ PUT И PATCH
@router.put("/{ozon_path:path}", summary="Проксирование PUT запросов")
async def proxy_put(
    ozon_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
    # 3. ВОЗВРАЩАЕМ ЯВНОЕ ОБЪЯВЛЕНИЕ ПАРАМЕТРОВ ДЛЯ SWAGGER
    body: Any = Body(None, description="Тело запроса в формате JSON"),
    x_target_client_id: int = Header(..., alias="X-Target-Client-ID", description="ID целевого клиента")
):
    return await _common_proxy_logic(request, db, current_user, ozon_path, x_target_client_id)

@router.patch("/{ozon_path:path}", summary="Проксирование PATCH запросов")
async def proxy_patch(
    ozon_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
    # 3. ВОЗВРАЩАЕМ ЯВНОЕ ОБЪЯВЛЕНИЕ ПАРАМЕТРОВ ДЛЯ SWAGGER
    body: Any = Body(None, description="Тело запроса в формате JSON"),
    x_target_client_id: int = Header(..., alias="X-Target-Client-ID", description="ID целевого клиента")
):
    return await _common_proxy_logic(request, db, current_user, ozon_path, x_target_client_id)

@router.delete("/{ozon_path:path}", summary="Проксирование DELETE запросов")
async def proxy_delete(
    ozon_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
    x_target_client_id: int = Header(..., alias="X-Target-Client-ID", description="ID целевого клиента")
):
    return await _common_proxy_logic(request, db, current_user, ozon_path, x_target_client_id)
