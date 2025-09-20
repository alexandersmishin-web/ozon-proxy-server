from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum


# Это стандартный "фундамент" для всех наших моделей
Base = declarative_base()


# Создаем перечисление для статуса контракта, чтобы избежать ошибок с текстом
class ContractStatus(enum.Enum):
    none = "none"
    pending = "pending"
    active = "active"


# Модель для хранения информации о наших клиентах (пользователях сайта)
class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    inn = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True)
    phone = Column(String, nullable=True)
    contract_status = Column(SQLAlchemyEnum(ContractStatus), default=ContractStatus.none)

    # Эти строки создают "связи" с другими таблицами
    ozon_auth = relationship("ClientOzonAuth", back_populates="client", uselist=False, cascade="all, delete-orphan")
    permissions = relationship("ClientPermission", back_populates="client", cascade="all, delete-orphan")
    warehouses = relationship("Warehouse", back_populates="client", cascade="all, delete-orphan")


# Модель для хранения ключей Ozon для каждого клиента
class ClientOzonAuth(Base):
    __tablename__ = "client_ozon_auth"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, unique=True)
    encrypted_ozon_client_id = Column(String, nullable=True)
    encrypted_ozon_api_key = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="ozon_auth")


# Модель для хранения разрешений (галочек) для каждого клиента
class ClientPermission(Base):
    __tablename__ = "client_permissions"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    permission_code = Column(String, nullable=False) # Например: 'get_orders', 'update_stocks'
    enabled = Column(Boolean, default=False)

    client = relationship("Client", back_populates="permissions")


# Модель для хранения складов клиента
class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    mp_warehouse_id = Column(String, nullable=False) # ID склада из Ozon
    warehouse_name = Column(String, nullable=True)  # Название, понятное пользователю
    enabled_for_client = Column(Boolean, default=True)

    client = relationship("Client", back_populates="warehouses")

