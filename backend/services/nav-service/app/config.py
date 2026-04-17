from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://invoice_user:invoice_pass_2024@localhost:5432/invoice_manager"
    DATABASE_URL_SYNC: str = "postgresql://invoice_user:invoice_pass_2024@localhost:5432/invoice_manager"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET: str = "invoice-manager-jwt-secret-change-in-production-2024"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 480

    # NAV
    NAV_ENCRYPTION_KEY: str = ""  # Fernet key for credential encryption

    # App
    APP_NAME: str = "NAV Online Számla Service"
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000,http://192.168.0.120:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
