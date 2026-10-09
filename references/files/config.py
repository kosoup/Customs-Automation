"""
애플리케이션 설정
환경변수 또는 .env 파일로 오버라이드 가능
"""
from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    # 앱
    APP_NAME: str = "KCS 전자상거래 수출신고 API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Mock 모드 (True = UNI-PASS 실전송 없이 테스트)
    MOCK_MODE: bool = True

    # UNI-PASS 환경
    UNIPASS_ENV: Literal["test", "production"] = "test"
    UNIPASS_AUTH_KEY: str = ""      # 관세청 발급 인증키
    SSL_VERIFY: bool = True

    # Java 서명 서비스
    JAVA_SIGNER_PORT: int = 8081
    AUTO_START_JAVA_SIGNER: bool = False

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173", "*"]

    # 로그
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
