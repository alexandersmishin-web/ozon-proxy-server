# In: routers/clients.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload # <-- 1. ИМПОРТИРУЕМ selectinload
from typing import List

# Абсолютные импорты
import models
import schemas
import crud
import security
from database import get_db
from security import get_current_superuser

router = APIRouter(
    prefix="/clients",
    tags=["Clients"]
)

# CREATE
@router.post(
    "/", 
    response_model=schemas.Client, 
    status_code=status.HTTP_201_CREATED,
    summary="Создать нового клиента и пользователя"
)
async def create_client_and_user_endpoint(
    payload: schemas.ClientCreateWithUser,
    db: AsyncSession = Depends(get_db),
    # Защита: только суперпользователь может создавать клиентов
    current_admin: models.User = Depends(security.get_current_superuser)
):
    """
    Создает нового клиента и связанного с ним пользователя.
    Выполняет проверку на дубликат логина перед созданием.
    Все операции выполняются в одной транзакции.
    """
    # 1. Проверяем, не занят ли логин
    db_user = await crud.get_user_by_login(db, login=payload.user_data.login)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким логином уже существует"
        )
        
    # 2. Если логин свободен, вызываем CRUD-функцию для создания
    try:
        new_client = await crud.create_client_with_user(
            db=db, 
            client_data=payload.client_data, 
            user_data=payload.user_data
        )
        return new_client
    except Exception as e:
        # Откатываем транзакцию в случае любой другой ошибки
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Произошла внутренняя ошибка при создании клиента: {e}"
        )

# READ (all)
@router.get("/", response_model=List[schemas.Client])
async def read_clients(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
    ):
    """Получает список всех клиентов."""
    clients = await crud.get_clients(db, skip=skip, limit=limit)
    return clients    
    # --- 3. ИСПРАВЛЕНИЕ: Добавляем "жадную" загрузку и для списка ---
    result = await db.execute(
        select(models.Client)
        .options(
            selectinload(models.Client.user),
            selectinload(models.Client.ozon_auth),
            selectinload(models.Client.permissions),
            selectinload(models.Client.warehouses).selectinload(models.ClientWarehouse.our_warehouse)
        )
        .offset(skip).limit(limit)
    )
    clients = result.scalars().all()
    return clients

# READ (one)
@router.get("/{client_id}", response_model=schemas.Client)
async def read_client(client_id: int, db: AsyncSession = Depends(get_db)):
    # --- 4. ИСПРАВЛЕНИЕ: Добавляем "жадную" загрузку для одного клиента ---
    result = await db.execute(
        select(models.Client)
        .options(
            selectinload(models.Client.user),
            selectinload(models.Client.ozon_auth),
            selectinload(models.Client.permissions),
            selectinload(models.Client.warehouses).selectinload(models.ClientWarehouse.our_warehouse)
        )
        .filter(models.Client.id == client_id)
    )
    db_client = result.scalars().first()
    if db_client is None:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    return db_client

# UPDATE
@router.patch("/{client_id}", response_model=schemas.Client)
async def update_client(client_id: int, client_update: schemas.ClientUpdate, db: AsyncSession = Depends(get_db)):
    """
    Обновляет данные клиента по ID. Позволяет обновлять только переданные поля.
    """
    result = await db.execute(select(models.Client).filter(models.Client.id == client_id))
    db_client = result.scalars().first()

    if db_client is None:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    update_data = client_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        if key == "password":
            setattr(db_client, "password_hash", f"{value}_hashed")
        else:
            setattr(db_client, key, value)

    db.add(db_client)
    await db.commit()
    # refresh() здесь не загружает связи, он только обновляет поля самого объекта
    await db.refresh(db_client)

    # --- ИСПРАВЛЕНИЕ: Повторно запрашиваем клиента с "жадной" загрузкой всех связей ---
    final_result = await db.execute(
        select(models.Client)
        .options(
            selectinload(models.Client.ozon_auth),
            selectinload(models.Client.permissions).selectinload(models.ClientPermission.permission), # <-- Загружаем даже вложенные связи
            selectinload(models.Client.warehouses).selectinload(models.ClientWarehouse.our_warehouse)
        )
        .filter(models.Client.id == client_id)
    )
    
    updated_client = final_result.scalars().first()
    return updated_client

# DELETE - этот метод не возвращает тело, поэтому исправления не нужны
@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(client_id: int, db: AsyncSession = Depends(get_db)):
    # ... код без изменений ...
    result = await db.execute(select(models.Client).filter(models.Client.id == client_id))
    db_client = result.scalars().first()

    if db_client is None:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    await db.delete(db_client)
    await db.commit()
    return None

