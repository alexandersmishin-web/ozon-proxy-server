# File: update_password.py

import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select

# Импортируем наши собственные модули
from settings import settings
import models
from security import get_password_hash # Наша функция для хэширования

async def main(login: str, new_pass: str):
    """
    Находит пользователя по логину и устанавливает ему новый пароль.
    """
    print(f"--- Попытка смены пароля для пользователя: {login} ---")
    
    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # Находим пользователя
        result = await session.execute(
            select(models.User).filter(models.User.login == login)
        )
        user_to_update = result.scalars().first()

        if not user_to_update:
            print(f"❌ ОШИБКА: Пользователь с логином '{login}' не найден.")
            return

        # Устанавливаем новый хэш пароля
        user_to_update.password_hash = get_password_hash(new_pass)
        session.add(user_to_update)
        await session.commit()
        
        print(f"✅ УСПЕХ: Пароль для пользователя '{login}' был успешно обновлен.")
            
    print("--- Скрипт завершил работу ---")

if __name__ == "__main__":
    # Простая проверка, что скрипт запущен с нужными аргументами
    if len(sys.argv) != 3:
        print("Использование: python update_password.py <login> <new_password>")
        sys.exit(1)
        
    user_login = sys.argv[1]
    new_password = sys.argv[2]
    asyncio.run(main(login=user_login, new_pass=new_password))
