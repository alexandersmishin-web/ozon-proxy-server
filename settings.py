# File: settings.py

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Настройки для базы данных
    database_url: str
    
    # Настройки для JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int # <-- 1. ДОБАВЛЕНО ЭТО ПОЛЕ
    
    # Ключ для шифрования Ozon ключей
    ozon_crypt_key: str

    # Эта строка говорит Pydantic всегда читать
    # переменные из файла с именем ".env"
    model_config = SettingsConfigDict(env_file=".env")

# Создаем единственный экземпляр настроек
settings = Settings()
