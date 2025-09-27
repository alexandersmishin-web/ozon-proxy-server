from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import JWTError, jwt
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()

import models
import schemas
import database
import utils
import crud
from settings import settings
from routers import permissions, clients, client_permissions, warehouses, ozon_auth, auth, proxy

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Событие при старте приложения ---
@app.on_event("startup")
async def on_startup():
    # Асинхронно создаем таблицы
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

# --- Зависимости ---
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(database.get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
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

# --- Эндпоинты ---
@app.post("/users/", response_model=schemas.Client)
async def create_user_route(user: schemas.ClientCreate, db: AsyncSession = Depends(database.get_db)):
    db_user = await crud.get_user_by_login(db, login=user.login)
    if db_user:
        raise HTTPException(status_code=400, detail="Login already registered")
    
    result = await db.execute(select(models.Client).filter(models.Client.inn == user.inn))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="INN already registered")

    return await utils.create_user(db=db, user=user)

@app.get("/users/me/", response_model=schemas.Client)
async def read_users_me(current_user: schemas.Client = Depends(get_current_user)):
    return current_user

@app.get("/")
def read_root():
    content = {"message": "Прокси-сервер готов к работе с клиентами!"}
    return JSONResponse(content=content, media_type="application/json; charset=utf-8")

from routers import permissions
app.include_router(permissions.router)
app.include_router(clients.router)
app.include_router(client_permissions.router)
app.include_router(warehouses.router)
app.include_router(ozon_auth.router)
app.include_router(auth.router)
app.include_router(proxy.router)