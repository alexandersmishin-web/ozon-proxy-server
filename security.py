from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from settings import settings # Импортируем наши настройки
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

import crud
from database import get_db
import schemas

# Указываем FastAPI, где искать токен
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
):
    """Декодирует токен, проверяет пользователя и возвращает его."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        login: str = payload.get("sub")
        if login is None:
            raise credentials_exception
        token_data = schemas.TokenData(login=login)
    except JWTError:
        raise credentials_exception
    
    user = await crud.get_user_by_login(db, login=token_data.login)
    if user is None:
        raise credentials_exception
    return user

# 1. Создаем контекст для хэширования. Он будет использовать алгоритм bcrypt.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 2. Функция для проверки пароля
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет, соответствует ли обычный пароль хэшированному."""
    return pwd_context.verify(plain_password, hashed_password)

# 3. Функция для получения хэша пароля
def get_password_hash(password: str) -> str:
    """Создает хэш из обычного пароля."""
    return pwd_context.hash(password)

# --- КОД ДЛЯ JWT ---

def create_access_token( dict, expires_delta: Optional[timedelta] = None):
    """Создает JWT-токен."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.jwt_secret_key, 
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt
