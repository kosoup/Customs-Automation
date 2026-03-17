from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./customs.db"
    UNIPASS_API_KEY: Optional[str] = None
    UTRADEHUB_API_KEY: Optional[str] = None
    UTRADEHUB_SENDER_ID: Optional[str] = None
    UTRADEHUB_RECEIVER_ID: str = "CUST0001"
    UPLOAD_DIR: str = "./uploads"

    class Config:
        env_file = ".env"


settings = Settings()
