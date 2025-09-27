# In: routers/proxy.py

from fastapi import (
    APIRouter, Request, Depends, HTTPException, 
    status, Body, Header, Response
)
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import httpx

# Импортируем наши собственные модули
import models
import security
from database import get_db

router = APIRouter(prefix="/proxy", tags=["Proxy"])


# =============================================================================
# 1. ОБЩАЯ "РАБОЧАЯ" ФУНКЦИЯ С ОСНОВНОЙ ЛОГИКОЙ
# =============================================================================
async def _common_proxy_logic(
    request: Request,
    db: AsyncSession,
    current_user: models.User,
    ozon_path: str,
    x_target_client_id: Optional[int],
    body: Optional[dict] = None,
):
    """
    Содержит всю основную логику проксирования. Вызывается из "тонких" эндпоинтов.
    """
    # Проверка, что запрос делает сотрудник
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Этот эндпоинт только для сотрудников."
        )

    # Проверка, что сотрудник указал, для какого клиента работать
    if x_target_client_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать ID целевого клиента в заголовке X-Target-Client-ID."
        )

    # Поиск ключей указанного клиента
    result = await db.execute(
        select(models.Client)
        .options(selectinload(models.Client.ozon_auth))
        .filter(models.Client.id == x_target_client_id)
    )
    target_client = result.scalars().first()

    if not target_client or not target_client.ozon_auth:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Клиент с ID {x_target_client_id} или его ключи Ozon не найдены."
        )
    
    # Расшифровка ключей
    try:
        decrypted_client_id = security.decrypt_data(target_client.ozon_auth.encrypted_ozon_client_id)
        decrypted_api_key = security.decrypt_data(target_client.ozon_auth.encrypted_ozon_api_key)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось расшифровать ключи Ozon."
        )

    # Формирование URL и заголовков
    ozon_api_url = f"https://api-seller.ozon.ru/{ozon_path}"
    headers_to_forward = {
        "Client-Id": decrypted_client_id,
        "Api-Key": decrypted_api_key,
        "Content-Type": request.headers.get("content-type", "application/json"),
    }
    
    # Выполнение запроса к Ozon API
    async with httpx.AsyncClient() as ozon_client:
        try:
            request_params = {
                "method": request.method,
                "url": ozon_api_url,
                "headers": headers_to_forward,
                "params": request.query_params,
                "timeout": 30.0,
            }
            if request.method.upper() not in ["GET", "DELETE", "HEAD", "OPTIONS"]:
                request_params["json"] = body

            response = await ozon_client.request(**request_params)

        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Ошибка соединения с Ozon API: {exc}"
            )

    # Возврат точного ответа от Ozon
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers)
    )

# =============================================================================
# 2. "ТОНКИЕ" ЭНДПОИНТЫ ДЛЯ КАЖДОГО HTTP-МЕТОДА
# =============================================================================

@router.post("/{ozon_path:path}", summary="Проксирование POST запросов")
async def proxy_post(
    ozon_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
    body: Optional[dict] = Body(None),
    x_target_client_id: Optional[int] = Header(None, alias="X-Target-Client-ID"),
):
    return await _common_proxy_logic(request, db, current_user, ozon_path, x_target_client_id, body)

@router.get("/{ozon_path:path}", summary="Проксирование GET запросов")
async def proxy_get(
    ozon_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
    x_target_client_id: Optional[int] = Header(None, alias="X-Target-Client-ID"),
):
    return await _common_proxy_logic(request, db, current_user, ozon_path, x_target_client_id)

@router.put("/{ozon_path:path}", summary="Проксирование PUT запросов")
async def proxy_put(
    ozon_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
    body: Optional[dict] = Body(None),
    x_target_client_id: Optional[int] = Header(None, alias="X-Target-Client-ID"),
):
    return await _common_proxy_logic(request, db, current_user, ozon_path, x_target_client_id, body)

@router.delete("/{ozon_path:path}", summary="Проксирование DELETE запросов")
async def proxy_delete(
    ozon_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
    x_target_client_id: Optional[int] = Header(None, alias="X-Target-Client-ID"),
):
    return await _common_proxy_logic(request, db, current_user, ozon_path, x_target_client_id)

@router.patch("/{ozon_path:path}", summary="Проксирование PATCH запросов")
async def proxy_patch(
    ozon_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
    body: Optional[dict] = Body(None),
    x_target_client_id: Optional[int] = Header(None, alias="X-Target-Client-ID"),
):
    return await _common_proxy_logic(request, db, current_user, ozon_path, x_target_client_id, body)
