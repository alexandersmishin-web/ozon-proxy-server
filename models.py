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

# --- МОДЕЛЬ USER ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    login = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False) # Флаг для ваших сотрудников (админов)
    is_temporary_password = Column(Boolean, default=True) # Флаг для смены пароля клиентом

    # Связь "один-к-одному" с клиентом
    client = relationship("Client", back_populates="user", uselist=False)

# Пользователь (клиент)
class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    inn = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    contract_status = Column(SQLAlchemyEnum(ContractStatus), default=ContractStatus.none)

    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    user = relationship("User", back_populates="client")
    ozon_auth = relationship("ClientOzonAuth", back_populates="client", uselist=False, cascade="all, delete-orphan")
    permissions = relationship("ClientPermission", back_populates="client", cascade="all, delete-orphan")
    warehouses = relationship("ClientWarehouse", back_populates="client", cascade="all, delete-orphan")

# Интеграция с Озон для клиента
class ClientOzonAuth(Base):
    __tablename__ = "client_ozon_auth"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, unique=True)
    encrypted_ozon_client_id = Column(String, nullable=False)
    encrypted_ozon_api_key = Column(String, nullable=False)
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

# Справочник НАШИХ складов
class OurWarehouse(Base):
    __tablename__ = "our_warehouses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    address = Column(String, nullable=False)
    sap_name = Column(String, nullable=True)
    sap_plant_code = Column(String, nullable=True)

    # Связь, чтобы видеть, какие склады клиентов на него ссылаются
    client_warehouses = relationship("ClientWarehouse", back_populates="our_warehouse")

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
class ClientWarehouse(Base):
    __tablename__ = "client_warehouses"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    mp_warehouse_id = Column(String, nullable=False)         # ID склада из Ozon

    # Внешний ключ, ссылающийся на наш справочник
    our_warehouse_id = Column(Integer, ForeignKey("our_warehouses.id"), nullable=False)

    # Связи
    client = relationship("Client", back_populates="warehouses")
    our_warehouse = relationship("OurWarehouse", back_populates="client_warehouses")

