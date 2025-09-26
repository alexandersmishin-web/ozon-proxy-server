from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from models import ContractStatus

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
    pass

class ClientPermissionUpdate(BaseModel):
    enabled: bool

class ClientPermission(ClientPermissionBase):
    id: int
    permission: PermissionRead   # вложенная инфа о праве

    class Config:
        from_attributes = True

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

class ClientUpdate(BaseModel):
    login: Optional[str] = None
    email: Optional[EmailStr] = None
    inn: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None # Для смены пароля

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
