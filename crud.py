# In: crud.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload 

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
async def create_client(db: AsyncSession, client_data: schemas.ClientCreate):
    """Создает нового пользователя и привязанного к нему клиента."""
    db_user = await get_user_by_login(db, login=client_data.login)
    if db_user:
        return None

    user_create_schema = schemas.UserCreate(
        login=client_data.login, password=client_data.password, email=client_data.email
    )
    new_user = await create_user(db, user=user_create_schema)

    db_client = models.Client(
        inn=client_data.inn,
        phone=client_data.phone,
        contract_status=client_data.contract_status,
        user_id=new_user.id
    )
    db.add(db_client)
    await db.commit()
    await db.refresh(db_client)

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

async def get_clients(db: AsyncSession, skip: int = 0, limit: int = 100):
    """Получает список клиентов с жадной загрузкой."""
    result = await db.execute(
        select(models.Client).options(
            selectinload(models.Client.user),
            selectinload(models.Client.ozon_auth),
            selectinload(models.Client.permissions).selectinload(models.ClientPermission.permission),
            selectinload(models.Client.warehouses).selectinload(models.ClientWarehouse.our_warehouse)
        ).offset(skip).limit(limit)
    )
    return result.scalars().all()

