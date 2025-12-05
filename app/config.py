# app/config.py
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # API Keys
    anthropic_api_key: str = ""

    # App Settings
    app_env: str = "development"
    debug: bool = True

    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000"
    ]

    class Config:
        env_file = ".env"
        case_sensitive = False


# ✅ ГЛАВНОЕ: создаём экземпляр
settings = Settings()
