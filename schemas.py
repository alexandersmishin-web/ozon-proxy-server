from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from models import ContractStatus

# ===================================================================
# --- Схемы для Пользователя (User) и Аутентификации ---
# ===================================================================

# Базовая схема пользователя
class UserBase(BaseModel):
    login: str
    email: Optional[EmailStr] = None

# Схема для создания пользователя (принимает пароль)
class UserCreate(UserBase):
    password: str

# Схема для обновления данных пользователя (email, пароль)
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None

# Схема для ответа API (не содержит пароль)
class User(UserBase):
    id: int
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True

# --- Схемы для Аутентификации (Токены) ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    login: Optional[str] = None


# ===================================================================
# --- Схемы для Клиента (Client) ---
# ===================================================================

class ClientBase(BaseModel):
    inn: Optional[str] = None
    phone: Optional[str] = None
    contract_status: Optional[str] = "none"

# Схема для создания КЛИЕНТА (включает создание Пользователя)
class ClientCreate(ClientBase):
    login: str
    password: str
    email: Optional[EmailStr] = None

# Схема для обновления данных КЛИЕНТА
class ClientUpdate(ClientBase):
    # Убрали email и password, так как они теперь в UserUpdate
    pass

# Полная схема клиента для ответов API
class Client(ClientBase):
    id: int
    user: User # Вложенная информация о пользователе
    
    # Связанные бизнес-сущности
    ozon_auth: Optional["ClientOzonAuth"] = None
    permissions: List["ClientPermission"] = []
    warehouses: List["ClientWarehouse"] = []

    class Config:
        from_attributes = True


# ===================================================================
# --- Схемы для Разрешений, Складов, Ключей Ozon ---
# (Этот код у вас уже правильный, оставляем без изменений)
# ===================================================================

# --- Схемы для СПРАВОЧНИКА Разрешений (Permission) ---
class PermissionBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_required: bool = False
    is_active: bool = True

class PermissionCreate(PermissionBase):
    pass

class PermissionRead(PermissionBase):
    id: int
    class Config:
        from_attributes = True

class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_required: Optional[bool] = None
    is_active: Optional[bool] = None

# --- Схемы для Связки Клиент-Разрешение ---
class ClientPermissionBase(BaseModel):
    enabled: bool = True

class ClientPermissionCreate(ClientPermissionBase):
    permission_id: int

class ClientPermissionUpdate(BaseModel):
    enabled: bool

class ClientPermission(ClientPermissionBase):
    id: int
    permission: PermissionRead
    class Config:
        from_attributes = True

# --- СХЕМЫ для справочника НАШИХ складов ---
class OurWarehouseBase(BaseModel):
    name: str
    address: str
    sap_name: Optional[str] = None
    sap_plant_code: Optional[str] = None

class OurWarehouseCreate(OurWarehouseBase):
    pass

class OurWarehouseUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    sap_name: Optional[str] = None
    sap_plant_code: Optional[str] = None

class OurWarehouse(OurWarehouseBase):
    id: int
    class Config:
        from_attributes = True

# --- Схемы для Складов КЛИЕНТА ---
class ClientWarehouseBase(BaseModel):
    mp_warehouse_id: str
    our_warehouse_id: int

class ClientWarehouseCreate(ClientWarehouseBase):
    pass

class ClientWarehouse(ClientWarehouseBase):
    id: int
    our_warehouse: OurWarehouse
    class Config:
        from_attributes = True

# --- Схемы для Ключей Ozon ---
class ClientOzonAuthCreate(BaseModel):
    ozon_client_id: str
    ozon_api_key: str

class ClientOzonAuth(BaseModel):
    id: int
    client_id: int
    updated_at: datetime
    class Config:
        from_attributes = True

# --- Схема для смены пароля ---
class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str

# Это нужно для Pydantic, чтобы он мог разрешить "отложенные" аннотации типов
Client.model_rebuild()
