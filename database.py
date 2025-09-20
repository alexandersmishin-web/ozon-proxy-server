from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./database.db"

# Асинхронный "движок" для SQLAlchemy
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Асинхронная сессия
SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)

Base = declarative_base()

# Асинхронная зависимость для получения сессии, которой не хватало
async def get_db():
    async with SessionLocal() as session:
        yield session
