# In: routers/clients.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload # <-- 1. ИМПОРТИРУЕМ selectinload
from typing import List

# Абсолютные импорты
import models
import schemas
from database import get_db

router = APIRouter(
    prefix="/clients",
    tags=["clients"],
)

# CREATE
@router.post("/", response_model=schemas.Client, status_code=status.HTTP_201_CREATED)
async def create_client(client: schemas.ClientCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Client).filter(models.Client.inn == client.inn))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Клиент с таким ИНН уже существует")

    hashed_password = f"{client.password}_hashed"
    new_client_data = client.dict(exclude={"password"})
    db_client = models.Client(**new_client_data, password_hash=hashed_password)

    db.add(db_client)
    await db.commit()
    await db.refresh(db_client) # <-- refresh() не загружает связи, поэтому нужен доп. запрос

    # --- 2. ИСПРАВЛЕНИЕ: Повторно запрашиваем клиента с "жадной" загрузкой связей ---
    result = await db.execute(
        select(models.Client)
        .options(
            selectinload(models.Client.ozon_auth),
            selectinload(models.Client.permissions),
            selectinload(models.Client.warehouses)
        )
        .filter(models.Client.id == db_client.id)
    )
    final_client = result.scalars().first()
    return final_client

# READ (all)
@router.get("/", response_model=List[schemas.Client])
async def read_clients(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    # --- 3. ИСПРАВЛЕНИЕ: Добавляем "жадную" загрузку и для списка ---
    result = await db.execute(
        select(models.Client)
        .options(
            selectinload(models.Client.ozon_auth),
            selectinload(models.Client.permissions),
            selectinload(models.Client.warehouses)
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
            selectinload(models.Client.ozon_auth),
            selectinload(models.Client.permissions),
            selectinload(models.Client.warehouses)
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
            selectinload(models.Client.warehouses)
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

