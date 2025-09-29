# File: check_superuser.py

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select

# Импортируем наши собственные модули
from settings import settings
import models

async def main():
    """
    Подключается к базе данных и проверяет наличие суперпользователя.
    """
    print("--- Проверка наличия суперпользователя ---")
    
    # Используем те же настройки, что и наше основное приложение
    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # Ищем в таблице users любого пользователя с флагом is_superuser = True
        result = await session.execute(
            select(models.User).filter(models.User.is_superuser == True)
        )
        superuser = result.scalars().first()

        if superuser:
            print("\n✅ УСПЕХ: Суперпользователь найден в базе данных!")
            print(f"   Логин: {superuser.login}")
            print(f"   ID: {superuser.id}")
            print(f"   Активен: {superuser.is_active}")
            if not superuser.is_active:
                print("\n   ⚠️ ПРЕДУПРЕЖДЕНИЕ: Этот пользователь неактивен и не сможет войти в систему.")
        else:
            print("\n❌ ОШИБКА: Суперпользователь не найден в базе данных.")
            print("   Пожалуйста, повторно запустите скрипт `create_superuser.py`, чтобы создать его.")
            
    print("\n--- Проверка завершена ---")

if __name__ == "__main__":
    asyncio.run(main())
