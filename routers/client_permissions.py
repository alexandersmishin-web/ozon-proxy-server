from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload # <-- 1. ИМПОРТИРУЕМ selectinload
from typing import List
from security import get_current_superuser

import models
import schemas
from database import get_db

router = APIRouter(
    prefix="/clients/{client_id}/permissions",
    tags=["Client Permissions"],
    dependencies=[Depends(get_current_superuser)]
)

# НАЗНАЧИТЬ ПРАВО КЛИЕНТУ (GRANT)
@router.post("/", response_model=schemas.ClientPermission, status_code=status.HTTP_201_CREATED)
async def grant_permission_to_client(
    client_id: int,
    permission_to_grant: schemas.ClientPermissionCreate,
    db: AsyncSession = Depends(get_db)
):
    # Код проверки существования клиента и права остается без изменений
    client_res = await db.execute(select(models.Client).filter(models.Client.id == client_id))
    if not client_res.scalars().first():
        raise HTTPException(status_code=404, detail=f"Клиент с id={client_id} не найден")

    perm_res = await db.execute(select(models.Permission).filter(models.Permission.id == permission_to_grant.permission_id))
    if not perm_res.scalars().first():
        raise HTTPException(status_code=404, detail=f"Право с id={permission_to_grant.permission_id} не найдено")
    
    # ... код проверки на дубликат ...
    existing_link = await db.execute(select(models.ClientPermission).filter(models.ClientPermission.client_id == client_id, models.ClientPermission.permission_id == permission_to_grant.permission_id))
    if existing_link.scalars().first():
        raise HTTPException(status_code=400, detail="Это право уже назначено данному клиенту")

    # Создаем новую связь
    db_client_permission = models.ClientPermission(
        client_id=client_id,
        permission_id=permission_to_grant.permission_id,
        enabled=permission_to_grant.enabled
    )
    db.add(db_client_permission)
    await db.commit()
    await db.refresh(db_client_permission)

    # --- 2. ИСПРАВЛЕНИЕ: Повторно запрашиваем созданную связь с "жадной" загрузкой ---
    result = await db.execute(
        select(models.ClientPermission)
        .options(selectinload(models.ClientPermission.permission)) # Говорим загрузить связанное право
        .filter(models.ClientPermission.id == db_client_permission.id)
    )
    final_link = result.scalars().first()
    return final_link

# ПОЛУЧИТЬ ВСЕ ПРАВА КЛИЕНТА (GET)
@router.get("/", response_model=List[schemas.ClientPermission])
async def get_client_permissions(client_id: int, db: AsyncSession = Depends(get_db)):
    # --- 3. ИСПРАВЛЕНИЕ: Добавляем "жадную" загрузку и сюда ---
    result = await db.execute(
        select(models.ClientPermission)
        .options(selectinload(models.ClientPermission.permission)) # Говорим загрузить связанное право
        .filter(models.ClientPermission.client_id == client_id)
    )
    permissions = result.scalars().all()
    if not permissions:
         raise HTTPException(status_code=404, detail=f"Для клиента с id={client_id} не найдено назначенных прав")
    return permissions

# DELETE - этот метод не возвращает тело, исправления не нужны
@router.delete("/{permission_link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_permission_from_client(client_id: int, permission_link_id: int, db: AsyncSession = Depends(get_db)):
    # ... код без изменений ...
    result = await db.execute(select(models.ClientPermission).filter(models.ClientPermission.id == permission_link_id, models.ClientPermission.client_id == client_id))
    db_client_permission = result.scalars().first()

    if db_client_permission is None:
        raise HTTPException(status_code=404, detail="Указанное право не найдено у данного клиента")

    await db.delete(db_client_permission)
    await db.commit()
    return None

