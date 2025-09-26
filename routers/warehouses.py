from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List

import models
import schemas
from database import get_db

router = APIRouter()

# ===================================================================
# === CRUD для справочника НАШИХ складов (OurWarehouse) ===
# ===================================================================

@router.post("/our_warehouses/", response_model=schemas.OurWarehouse, status_code=status.HTTP_201_CREATED, tags=["Admin: Our Warehouses"])
async def create_our_warehouse(warehouse: schemas.OurWarehouseCreate, db: AsyncSession = Depends(get_db)):
    """Создает новый склад в вашем внутреннем справочнике."""
    db_warehouse = models.OurWarehouse(**warehouse.dict())
    db.add(db_warehouse)
    await db.commit()
    await db.refresh(db_warehouse)
    return db_warehouse

@router.get("/our_warehouses/", response_model=List[schemas.OurWarehouse], tags=["Admin: Our Warehouses"])
async def read_our_warehouses(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Возвращает список всех складов из вашего справочника."""
    result = await db.execute(select(models.OurWarehouse).offset(skip).limit(limit))
    return result.scalars().all()

# --- НОВЫЙ ЭНДПОИНТ ---
@router.get("/our_warehouses/{warehouse_id}", response_model=schemas.OurWarehouse, tags=["Admin: Our Warehouses"])
async def read_our_warehouse(warehouse_id: int, db: AsyncSession = Depends(get_db)):
    """Возвращает один склад из справочника по его ID."""
    db_warehouse = await db.get(models.OurWarehouse, warehouse_id)
    if not db_warehouse:
        raise HTTPException(status_code=404, detail="Склад не найден в справочнике")
    return db_warehouse

# --- НОВЫЙ ЭНДПОИНТ ---
@router.patch("/our_warehouses/{warehouse_id}", response_model=schemas.OurWarehouse, tags=["Admin: Our Warehouses"])
async def update_our_warehouse(
    warehouse_id: int,
    warehouse_update: schemas.OurWarehouseUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Частично обновляет данные склада в справочнике."""
    db_warehouse = await db.get(models.OurWarehouse, warehouse_id)
    if not db_warehouse:
        raise HTTPException(status_code=404, detail="Склад не найден в справочнике")

    update_data = warehouse_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_warehouse, key, value)

    db.add(db_warehouse)
    await db.commit()
    await db.refresh(db_warehouse)
    return db_warehouse

# --- НОВЫЙ ЭНДПОИНТ ---
@router.delete("/our_warehouses/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Admin: Our Warehouses"])
async def delete_our_warehouse(warehouse_id: int, db: AsyncSession = Depends(get_db)):
    """Удаляет склад из справочника."""
    db_warehouse = await db.get(models.OurWarehouse, warehouse_id)
    if not db_warehouse:
        raise HTTPException(status_code=404, detail="Склад не найден в справочнике")
    await db.delete(db_warehouse)
    await db.commit()
    return None

# ===================================================================
# === CRUD для привязки складов КЛИЕНТОВ (ClientWarehouse) ===
# ===================================================================

@router.post("/clients/{client_id}/warehouses/", response_model=schemas.ClientWarehouse, tags=["Client Warehouses"])
async def link_client_warehouse(
    client_id: int,
    warehouse: schemas.ClientWarehouseCreate,
    db: AsyncSession = Depends(get_db)
):
    # (код без изменений)
    client = await db.get(models.Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    our_warehouse = await db.get(models.OurWarehouse, warehouse.our_warehouse_id)
    if not our_warehouse:
        raise HTTPException(status_code=404, detail="Склад из справочника не найден")

    db_client_warehouse = models.ClientWarehouse(**warehouse.dict(), client_id=client_id)
    db.add(db_client_warehouse)
    await db.commit()
    await db.refresh(db_client_warehouse)
    
    result = await db.execute(
        select(models.ClientWarehouse)
        .options(selectinload(models.ClientWarehouse.our_warehouse))
        .filter(models.ClientWarehouse.id == db_client_warehouse.id)
    )
    return result.scalars().first()

@router.get("/clients/{client_id}/warehouses/", response_model=List[schemas.ClientWarehouse], tags=["Client Warehouses"])
async def read_client_warehouses(client_id: int, db: AsyncSession = Depends(get_db)):
    # (код без изменений, но с "жадной" загрузкой)
    result = await db.execute(
        select(models.ClientWarehouse)
        .options(selectinload(models.ClientWarehouse.our_warehouse))
        .filter(models.ClientWarehouse.client_id == client_id)
    )
    return result.scalars().all()

@router.delete("/client_warehouses/{client_warehouse_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Client Warehouses"])
async def unlink_client_warehouse(client_warehouse_id: int, db: AsyncSession = Depends(get_db)):
    # (код без изменений)
    db_link = await db.get(models.ClientWarehouse, client_warehouse_id)
    if not db_link:
        raise HTTPException(status_code=404, detail="Привязка склада не найдена")
    await db.delete(db_link)
    await db.commit()
    return None
