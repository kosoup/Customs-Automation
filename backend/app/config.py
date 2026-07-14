from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./customs.db"
    UNIPASS_API_KEY: Optional[str] = None  # unipass_tracker 용

    # UNI-PASS 조회 API 키 (4종)
    UNIPASS_KEY_HS_NAVI: Optional[str] = None
    UNIPASS_KEY_HS_SEARCH: Optional[str] = None
    UNIPASS_KEY_CUSTOMS_CHECK: Optional[str] = None
    UNIPASS_KEY_TARIFF: Optional[str] = None

    UTRADEHUB_API_KEY: Optional[str] = None
    UTRADEHUB_SENDER_ID: Optional[str] = None
    UTRADEHUB_RECEIVER_ID: str = "CUST0001"
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
    CORS_ORIGINS: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
