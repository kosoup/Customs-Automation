"""
KCS 전자상거래 수출신고 FastAPI 서버
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.declaration import router as declaration_router
from app.services.signer import start_java_signer, stop_java_signer

# ── 로깅 ──────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── 라이프사이클 ──────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"=== {settings.APP_NAME} v{settings.APP_VERSION} 시작 ===")
    logger.info(f"  MOCK_MODE     : {settings.MOCK_MODE}")
    logger.info(f"  UNIPASS_ENV   : {settings.UNIPASS_ENV}")
    logger.info(f"  JAVA_SIGNER   : port {settings.JAVA_SIGNER_PORT}")

    if settings.AUTO_START_JAVA_SIGNER:
        start_java_signer()

    yield

    stop_java_signer()
    logger.info("서버 종료")


# ── FastAPI 앱 ────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## 관세청 전자상거래 수출신고 API

WCO `KCS_DeclarationOfEXP_DJPSchemaModule:1:0` 스키마 기반 수출신고서를 처리합니다.

### 처리 흐름
1. **POST /api/declaration/xml** → XML 미리보기
2. **POST /api/declaration/validate** → XSD 스키마 검증
3. **POST /api/declaration/sign** → 공인인증서 전자서명
4. **POST /api/declaration/submit** → UNI-PASS 전송
5. **POST /api/declaration/full** → 전체 일괄 처리

### Mock 모드
`.env`에서 `MOCK_MODE=true`(기본값) 설정 시 실제 UNI-PASS 미연동 상태에서도 테스트 가능합니다.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 라우터 ────────────────────────────────────────────────────────────────────
app.include_router(declaration_router)

# ── 전역 예외 처리 ─────────────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"처리되지 않은 예외: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"서버 내부 오류: {type(exc).__name__}"},
    )

@app.get("/", tags=["루트"])
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "mock_mode": settings.MOCK_MODE,
    }
