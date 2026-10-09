from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db.session import Base, get_db
from app.main import app
from app.services.parser.base import ParsedInvoice
from app.services.parser.excel_parser import ExcelParser


@pytest_asyncio.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_health(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_declaration_lifecycle_uses_isolated_database(
    client: httpx.AsyncClient,
) -> None:
    payload = {
        "declarant_code": "A1234",
        "exporter_name": "테스트 수출자",
        "buyer_name": "Test Buyer",
        "buyer_country_code": "US",
        "destination_country_code": "US",
        "invoice_number": "INV-API-001",
        "currency_code": "USD",
        "incoterms": "FOB",
        "total_amount": 25.5,
        "net_weight_kg": 9.5,
        "gross_weight_kg": 10,
        "items": [
            {
                "item_seq": 1,
                "product_name_en": "Widget",
                "hscode": "1234567890",
                "quantity": 2,
                "unit": "EA",
                "unit_price": 12.75,
                "amount": 25.5,
            }
        ],
    }

    created = await client.post("/api/declarations", json=payload)
    assert created.status_code == 201
    declaration_id = created.json()["id"]

    validation = await client.post(f"/api/declarations/{declaration_id}/validate")
    assert validation.status_code == 200
    assert validation.json() == {"valid": True, "errors": []}

    invalid_submit = await client.post(
        f"/api/declarations/{declaration_id}/submit",
        params={"method": "unknown"},
    )
    assert invalid_submit.status_code == 400
    assert invalid_submit.json()["detail"] == "지원하지 않는 제출 방식: unknown"

    fetched = await client.get(f"/api/declarations/{declaration_id}")
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "validated"

    stats = await client.get("/api/declarations/stats/summary")
    assert stats.status_code == 200
    assert stats.json()["total"] == 1
    assert stats.json()["validated"] == 1

    invalid_export = await client.get(
        f"/api/declarations/{declaration_id}/export-file",
        params={"fmt": "pdf"},
    )
    assert invalid_export.status_code == 400
    assert invalid_export.json()["detail"] == "지원하지 않는 내보내기 형식: pdf"


@pytest.mark.asyncio
async def test_invoice_upload_rejects_legacy_xls_without_writing_file(
    client: httpx.AsyncClient,
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

    response = await client.post(
        "/api/invoices/upload",
        files={"file": ("legacy.xls", b"not-an-xls", "application/vnd.ms-excel")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "지원하지 않는 파일 형식입니다: .xls"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_invoice_upload_rejects_template_path_traversal_without_writing_file(
    client: httpx.AsyncClient,
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

    response = await client.post(
        "/api/invoices/upload",
        data={"template_name": "../../secrets"},
        files={
            "file": (
                "invoice.xlsx",
                b"synthetic",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "템플릿 이름 형식이 올바르지 않습니다"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_invoice_upload_removes_file_when_parsing_fails(
    client: httpx.AsyncClient,
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

    response = await client.post(
        "/api/invoices/upload",
        files={
            "file": (
                "../../broken.xlsx",
                b"not-an-xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"].startswith("파일 파싱 실패:")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_invoice_upload_rejects_oversized_file_and_removes_partial_file(
    client: httpx.AsyncClient,
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "MAX_UPLOAD_BYTES", 8)

    response = await client.post(
        "/api/invoices/upload",
        files={
            "file": (
                "large.xlsx",
                b"123456789",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "파일 크기는 8바이트를 초과할 수 없습니다"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_invoice_upload_normalizes_filename(
    client: httpx.AsyncClient,
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(
        ExcelParser,
        "parse",
        lambda self, file_path, template: ParsedInvoice(
            exporter_name="Synthetic Exporter",
            buyer_name="Synthetic Buyer",
            invoice_number="INV-SAFE-001",
        ),
    )

    response = await client.post(
        "/api/invoices/upload",
        files={
            "file": (
                "../../invoice.xlsx",
                b"synthetic",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 201
    assert response.json()["invoice"]["filename"] == "invoice.xlsx"
    saved_files = list(tmp_path.iterdir())
    assert len(saved_files) == 1
    assert saved_files[0].name.endswith("_invoice.xlsx")
