# In: crud.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload 
from typing import List, Optional

import models
import schemas
import security

# --- Функции для работы с User ---
async def get_user_by_login(db: AsyncSession, login: str):
    """Ищет пользователя по логину."""
    result = await db.execute(select(models.User).filter(models.User.login == login))
    return result.scalars().first()

async def create_user(db: AsyncSession, user: schemas.UserCreate):
    """Создает нового пользователя."""
    hashed_password = security.get_password_hash(user.password)
    db_user = models.User(
        login=user.login,
        email=user.email,
        password_hash=hashed_password,
        # is_temporary_password остается True по умолчанию
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

# --- Функции для работы с Client ---
async def create_client_with_user(db: AsyncSession, client_data: schemas.ClientCreate, user_data: schemas.UserCreate) -> models.Client:
    """
    Атомарно создает пользователя и связанного с ним клиента.
    Гарантированно подгружает все связи перед возвратом.
    """
    # Локальный импорт для разрыва циклической зависимости
    from security import get_password_hash 
    
    # 1. Создаем объекты в памяти (БЕЗ КОММИТА)
    hashed_password = get_password_hash(user_data.password)
    db_user = models.User(
        login=user_data.login,
        email=user_data.email,
        password_hash=hashed_password,
    )
    
    # Связываем пользователя и клиента сразу
    db_client = models.Client(**client_data.model_dump(), user=db_user)
    
    # 2. Добавляем оба объекта в сессию
    db.add(db_client)
    
    # 3. Коммитим все вместе
    await db.commit()
    
    # 4. --- ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ ---
    # Обновляем ТОЛЬКО что созданный объект, чтобы SQLAlchemy
    # подгрузил его связи в рамках ТОЙ ЖЕ активной сессии.
    await db.refresh(db_client, ['user', 'permissions', 'ozon_auth', 'warehouses'])
    
    return db_client

# --- Функции для работы с OzonAuth ---

async def get_ozon_auth_by_client_id(db: AsyncSession, client_id: int):
    """Ищет запись с ключами Ozon по ID клиента."""
    result = await db.execute(
        select(models.ClientOzonAuth).filter(models.ClientOzonAuth.client_id == client_id)
    )
    return result.scalars().first()

    # --- 2. ВОТ КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ ---
    # После создания мы заново запрашиваем клиента, но уже с "жадной" загрузкой всех связей.
    # Это гарантирует, что все данные будут доступны для Pydantic.
    result = await db.execute(
        select(models.Client).options(
            selectinload(models.Client.user),
            selectinload(models.Client.ozon_auth),
            selectinload(models.Client.permissions).selectinload(models.ClientPermission.permission), # Загружаем и сами права
            selectinload(models.Client.warehouses).selectinload(models.ClientWarehouse.our_warehouse) # Загружаем и наши склады
        ).filter(models.Client.id == db_client.id)
    )
    return result.scalars().first()

async def get_clients(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[models.Client]:
    """
    Получает список клиентов с принудительной загрузкой ВСЕХ связей.
    """
    result = await db.execute(
        select(models.Client).options(
            selectinload(models.Client.user),
            selectinload(models.Client.ozon_auth),
            # Вложенная "жадная" загрузка решает ошибку с MissingGreenlet
            selectinload(models.Client.permissions).selectinload(models.ClientPermission.permission),
            selectinload(models.Client.warehouses).selectinload(models.ClientWarehouse.our_warehouse)
        ).offset(skip).limit(limit)
    )
    return result.scalars().all()

async def get_client(db: AsyncSession, client_id: int) -> models.Client | None:
    """
    Получает одного клиента по ID с принудительной загрузкой ВСЕХ связей.
    """
    result = await db.execute(
        select(models.Client).options(
            selectinload(models.Client.user),
            selectinload(models.Client.ozon_auth),
            selectinload(models.Client.permissions).selectinload(models.ClientPermission.permission),
            selectinload(models.Client.warehouses).selectinload(models.ClientWarehouse.our_warehouse)
        ).filter(models.Client.id == client_id)
    )
    return result.scalars().first()


async def assign_permission_to_client(
    db: AsyncSession, client_id: int, permission_id: int, enabled: bool
) -> models.ClientPermission:
    """
    Назначает право клиенту. Если право уже было назначено,
    обновляет его статус (enabled/disabled).
    """
    # Ищем существующую связь
    result = await db.execute(
        select(models.ClientPermission).filter_by(client_id=client_id, permission_id=permission_id)
    )
    db_client_permission = result.scalars().first()

    if db_client_permission:
        # Если нашли - обновляем статус
        db_client_permission.enabled = enabled
    else:
        # Если не нашли - создаем новую связь
        db_client_permission = models.ClientPermission(
            client_id=client_id, permission_id=permission_id, enabled=enabled
        )
        db.add(db_client_permission)
    
    await db.commit()
    await db.refresh(db_client_permission)
    return db_client_permission

async def get_client_permissions(db: AsyncSession, client_id: int) -> List[models.ClientPermission]:
    """Возвращает список всех прав, назначенных конкретному клиенту."""
    result = await db.execute(
        select(models.ClientPermission).filter(models.ClientPermission.client_id == client_id)
    )
    return result.scalars().all()

async def check_client_permission(db: AsyncSession, client_id: int, permission_name: str) -> bool:
    """
    Проверяет, есть ли у клиента конкретное и ВКЛЮЧЕННОЕ право.
    Это ключевая функция для нашего прокси.
    """
    result = await db.execute(
        select(models.ClientPermission)
        .join(models.Permission)
        .filter(
            models.ClientPermission.client_id == client_id,
            models.Permission.name == permission_name,
            models.ClientPermission.enabled == True
        )
    )
    return result.scalars().first() is not None    