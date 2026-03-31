from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./customs.db"
    UNIPASS_API_KEY: Optional[str] = None  # unipass_tracker 용

    # UNI-PASS 조회 API 키 (4종)
    UNIPASS_KEY_HS_NAVI: str = "q260c205y132u009k080o020d0"
    UNIPASS_KEY_HS_SEARCH: str = "m250o275s132p039a030c090t0"
    UNIPASS_KEY_CUSTOMS_CHECK: str = "i280x285t122x079u070y060l0"
    UNIPASS_KEY_TARIFF: str = "z290u255b132v214x040m000q0"

    UTRADEHUB_API_KEY: Optional[str] = None
    UTRADEHUB_SENDER_ID: Optional[str] = None
    UTRADEHUB_RECEIVER_ID: str = "CUST0001"
    UPLOAD_DIR: str = "./uploads"

    class Config:
        env_file = ".env"


settings = Settings()
