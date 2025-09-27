from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Ключ для шифрования данных. ДОЛЖЕН БЫТЬ СГЕНЕРИРОВАН И ХРАНИТЬСЯ В .env ФАЙЛЕ
    ozon_crypt_key: str
    database_url: str
    # Настройки для JWT токенов
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int

    class Config:
        env_file = ".env"

settings = Settings()
