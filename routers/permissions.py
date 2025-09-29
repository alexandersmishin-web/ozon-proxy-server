# In: routers/permissions.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

# Абсолютные импорты, которые мы исправили
import models
import schemas
from database import get_db
from security import get_current_superuser

router = APIRouter(
    prefix="/permissions",
    tags=["Permissions"],
    dependencies=[Depends(get_current_superuser)]
)

# CREATE
@router.post(
    "/",
    response_model=schemas.PermissionRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Право доступа успешно создано",
        }
    }
)
async def create_permission(permission: schemas.PermissionCreate, db: AsyncSession = Depends(get_db)):
    """
    Создает новое право доступа в справочнике.
    Доступно только суперпользователям.
    """
    result = await db.execute(select(models.Permission).filter(models.Permission.name == permission.name))
    db_perm = result.scalars().first()
    
    if db_perm:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Право с таким именем уже существует")

    new_perm = models.Permission(**permission.dict())
    db.add(new_perm)
    await db.commit()
    await db.refresh(new_perm)
    return new_perm

# READ (all)
@router.get("/", response_model=List[schemas.PermissionRead])
async def read_permissions(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """
    Возвращает список всех прав из справочника.
    """
    result = await db.execute(select(models.Permission).offset(skip).limit(limit))
    permissions = result.scalars().all()
    return permissions

# READ (one)
@router.get("/{permission_id}", response_model=schemas.PermissionRead)
async def read_permission(permission_id: int, db: AsyncSession = Depends(get_db)):
    """
    Возвращает одно право по его ID.
    """
    result = await db.execute(select(models.Permission).filter(models.Permission.id == permission_id))
    db_perm = result.scalars().first()
    
    if db_perm is None:
        raise HTTPException(status_code=404, detail="Право не найдено")
    return db_perm

# UPDATE
@router.put("/{permission_id}", response_model=schemas.PermissionRead)
async def update_permission(
    permission_id: int,
    permission_update: schemas.PermissionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Обновляет данные права доступа в справочнике по его ID.
    """
    result = await db.execute(select(models.Permission).filter(models.Permission.id == permission_id))
    db_perm = result.scalars().first()

    if db_perm is None:
        raise HTTPException(status_code=404, detail="Право не найдено")

    update_data = permission_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_perm, key, value)

    db.add(db_perm)
    await db.commit()
    await db.refresh(db_perm)
    return db_perm

# DELETE
@router.delete("/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(permission_id: int, db: AsyncSession = Depends(get_db)):
    """
    Удаляет право из справочника.
    """
    result = await db.execute(select(models.Permission).filter(models.Permission.id == permission_id))
    db_perm = result.scalars().first()

    if db_perm is None:
        raise HTTPException(status_code=404, detail="Право не найдено")

    await db.delete(db_perm)
    await db.commit()
    return None
