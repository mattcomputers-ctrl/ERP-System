from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "BatchFlow ERP"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://batchflow:batchflow@localhost:5432/batchflow_erp"

    # JWT
    SECRET_KEY: str = "change-this-to-a-secure-random-string-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    # QuickBooks Sync
    QB_SYNC_ENABLED: bool = False
    QB_SYNC_INTERVAL_SECONDS: int = 300

    # File storage
    UPLOAD_DIR: str = "/var/lib/batchflow/uploads"
    LOG_DIR: str = "/var/log/batchflow"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
