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

Base = declarative_base()

# Перечисление для статуса контракта
class ContractStatus(enum.Enum):
    none = "none"
    pending = "pending"
    active = "active"

# Пользователь (клиент)
class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    inn = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True)
    phone = Column(String, nullable=True)
    contract_status = Column(SQLAlchemyEnum(ContractStatus), default=ContractStatus.none)

    ozon_auth = relationship("ClientOzonAuth", back_populates="client", uselist=False, cascade="all, delete-orphan")
    permissions = relationship("ClientPermission", back_populates="client", cascade="all, delete-orphan")
    warehouses = relationship("Warehouse", back_populates="client", cascade="all, delete-orphan")

# Интеграция с Озон для клиента
class ClientOzonAuth(Base):
    __tablename__ = "client_ozon_auth"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, unique=True)
    encrypted_ozon_client_id = Column(String, nullable=True)
    encrypted_ozon_api_key = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="ozon_auth")

# СПРАВОЧНИК всех возможных прав
class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)       # machine-name: например, 'get_orders'
    description = Column(String, nullable=True)              # человеческое описание
    is_required = Column(Boolean, default=False)             # обязательно для работы
    is_active = Column(Boolean, default=True)
    # связи
    clients = relationship("ClientPermission", back_populates="permission")

# Связка: какое право выдал какой клиент
class ClientPermission(Base):
    __tablename__ = "client_permissions"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False)
    enabled = Column(Boolean, default=False)

    client = relationship("Client", back_populates="permissions")
    permission = relationship("Permission", back_populates="clients")

# Модель для хранения складов клиента
class Warehouse(Base):
    __tablename__ = "warehouses"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    mp_warehouse_id = Column(String, nullable=False)         # ID склада из Ozon
    warehouse_name = Column(String, nullable=True)           # Название, понятное пользователю
    enabled_for_client = Column(Boolean, default=True)

    client = relationship("Client", back_populates="warehouses")
