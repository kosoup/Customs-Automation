from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import engine, Base
from app.api.declarations import router as declarations_router
from app.api.invoices import router as invoices_router
from app.api.submissions import router as submissions_router
import app.models.invoice     # noqa: F401 - 테이블 등록
import app.models.submission   # noqa: F401 - 테이블 등록


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="수출통관 자동화", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(declarations_router)
app.include_router(invoices_router)
app.include_router(submissions_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
