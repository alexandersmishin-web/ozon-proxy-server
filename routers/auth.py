from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from settings import settings

import models
import schemas
import crud # Мы создадим этот файл на следующем шаге
import security
from database import get_db

router = APIRouter(tags=["Authentication"])

@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db)
):
    """
    Эндпоинт для входа. Принимает login и password, возвращает access_token.
    """
    # 1. Ищем пользователя в базе
    user = await crud.get_user_by_login(db, login=form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. Проверяем пароль
    if not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # 3. Создаем токен
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = security.create_access_token(
        data={"sub": user.login}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(security.get_current_user)):
    """Получает информацию о текущем аутентифицированном пользователе."""
    return current_user

@router.patch("/users/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def update_current_user_password(
    password_data: schemas.PasswordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    Позволяет аутентифицированному пользователю сменить свой пароль.
    """
    # 1. Проверяем, что старый пароль, введенный пользователем, верен
    if not security.verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный старый пароль",
        )
    
    # 2. Устанавливаем новый пароль и снимаем флаг временного пароля
    current_user.password_hash = security.get_password_hash(password_data.new_password)
    current_user.is_temporary_password = False
    
    db.add(current_user)
    await db.commit()