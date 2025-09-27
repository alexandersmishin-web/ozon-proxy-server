from sqlalchemy.orm import Session, selectinload
from sqlalchemy.future import select
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
from jose import jwt

import models
import schemas
from settings import settings

# --- Шифрование ---
try:
    fernet = Fernet(settings.ENCRYPTION_KEY.encode())
except Exception:
    fernet = None

def encrypt_data( str) -> str:
    if not fernet:
        raise ValueError("Encryption key is not initialized correctly.")
    return fernet.encrypt(data.encode()).decode()

def decrypt_data(encrypted_str: str) -> str:
    if not fernet:
        raise ValueError("Encryption key is not initialized correctly.")
    return fernet.decrypt(encrypted_str.encode()).decode()

# --- Логика паролей и токенов ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt

# --- АСИНХРОННЫЕ Функции для работы с базой данных ---
async def create_user(db: Session, user: schemas.ClientCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.Client(
        login=user.login,
        password_hash=hashed_password,
        email=user.email,
        inn=user.inn,
        phone=user.phone
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    # --- ВОТ КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ ---
    # Мы должны заново получить пользователя из БД, но уже с "жадной" загрузкой связей.
    # Это предотвратит ошибку MissingGreenlet при формировании ответа.
    result = await db.execute(
        select(models.Client)
        .options(
            selectinload(models.Client.ozon_auth),
            selectinload(models.Client.permissions),
            selectinload(models.Client.warehouses)
        )
        .filter(models.Client.id == db_user.id)
    )
    return result.scalars().first()

