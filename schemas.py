from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# Исправленный импорт без точки
from models import ContractStatus

# --- Схемы для Складов (Warehouse) ---
class WarehouseBase(BaseModel):
    mp_warehouse_id: str
    warehouse_name: Optional[str] = None

class WarehouseCreate(WarehouseBase):
    pass

class Warehouse(WarehouseBase):
    id: int
    enabled_for_client: bool

    class Config:
        from_attributes = True

# --- Схемы для Разрешений (Permissions) ---
class ClientPermissionBase(BaseModel):
    permission_code: str
    enabled: bool

class ClientPermissionCreate(ClientPermissionBase):
    pass

class ClientPermission(ClientPermissionBase):
    id: int

    class Config:
        from_attributes = True

# --- Схемы для Ключей Ozon ---
class ClientOzonAuthBase(BaseModel):
    ozon_client_id: str
    ozon_api_key: str

class ClientOzonAuthCreate(ClientOzonAuthBase):
    pass

class ClientOzonAuth(BaseModel):
    ozon_client_id: str
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Схемы для Клиента (User) ---
class ClientBase(BaseModel):
    login: str
    email: EmailStr
    inn: str
    phone: Optional[str] = None

class ClientCreate(ClientBase):
    password: str

class Client(ClientBase):
    id: int
    contract_status: ContractStatus
    ozon_auth: Optional[ClientOzonAuth] = None
    permissions: List[ClientPermission] = []
    warehouses: List[Warehouse] = []

    class Config:
        from_attributes = True

# --- Схемы для Аутентификации ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    login: Optional[str] = None
