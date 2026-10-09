from collections.abc import AsyncIterator
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from lxml import etree
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db.session import Base, get_db
from app.main import app
from app.models.declaration import Declaration
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


@pytest.mark.asyncio
@pytest.mark.parametrize('export_path', ['export-xml', 'export-file?fmt=csv', 'export-file?fmt=xlsx'])
async def test_invalid_draft_cannot_be_exported(client: httpx.AsyncClient, export_path: str) -> None:
    created = await client.post('/api/declarations', json={})
    declaration_id = created.json()['id']
    validation = await client.post(f'/api/declarations/{declaration_id}/validate')
    assert validation.json()['valid'] is False
    response = await client.get(f'/api/declarations/{declaration_id}/{export_path}')
    assert response.status_code == 400


async def _create_validated_declaration(client: httpx.AsyncClient) -> int:
    created = await client.post('/api/declarations', json={
        'exporter_name': 'Synthetic Exporter', 'buyer_name': 'Synthetic Buyer',
        'buyer_country_code': 'US', 'invoice_number': 'SYN-STATE-001',
        'currency_code': 'USD', 'total_amount': 25.5,
        'items': [{'item_seq': 1, 'product_name_en': 'Widget', 'hscode': '1234567890',
                   'quantity': 2, 'unit': 'EA', 'unit_price': 12.75, 'amount': 25.5}],
    })
    assert created.status_code == 201
    declaration_id = created.json()['id']
    validation = await client.post(f'/api/declarations/{declaration_id}/validate')
    assert validation.json()['valid'] is True
    return declaration_id


@pytest.mark.asyncio
async def test_file_export_record_keeps_declaration_editable(client: httpx.AsyncClient) -> None:
    declaration_id = await _create_validated_declaration(client)
    response = await client.post(f'/api/declarations/{declaration_id}/submit?method=file_export')
    assert response.status_code == 201
    current = await client.get(f'/api/declarations/{declaration_id}')
    assert current.json()['status'] == 'validated'
    assert current.json()['submission_ref'] is None
    edit = await client.put(f'/api/declarations/{declaration_id}', json={'buyer_name': 'Updated Synthetic Buyer'})
    assert edit.status_code == 200
    assert edit.json()['status'] == 'draft'
    assert (await client.get(f'/api/declarations/{declaration_id}/export-xml')).status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize('terminal_status', ['submitted', 'accepted', 'rejected'])
async def test_validation_cannot_reopen_terminal_declaration(
    client: httpx.AsyncClient, terminal_status: str,
) -> None:
    declaration_id = await _create_validated_declaration(client)
    async for db in app.dependency_overrides[get_db]():
        await db.execute(update(Declaration).where(Declaration.id == declaration_id).values(status=terminal_status))
        await db.commit()
    response = await client.post(f'/api/declarations/{declaration_id}/validate')
    assert response.status_code == 400
    current = await client.get(f'/api/declarations/{declaration_id}')
    assert current.json()['status'] == terminal_status


@pytest.mark.asyncio
async def test_export_rechecks_contents_even_if_status_is_validated(client: httpx.AsyncClient) -> None:
    declaration_id = await _create_validated_declaration(client)
    async for db in app.dependency_overrides[get_db]():
        await db.execute(update(Declaration).where(Declaration.id == declaration_id).values(buyer_country_code='USA'))
        await db.commit()
    for path in ['export-xml', 'export-file?fmt=csv', 'export-file?fmt=xlsx']:
        assert (await client.get(f'/api/declarations/{declaration_id}/{path}')).status_code == 400


@pytest.mark.asyncio
async def test_synthetic_pdf_upload_review_and_export(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, 'UPLOAD_DIR', str(tmp_path))
    fixture = Path(__file__).parent / 'fixtures' / 'synthetic-invoice.pdf'
    response = await client.post('/api/invoices/upload', files={
        'file': ('synthetic-invoice.pdf', fixture.read_bytes(), 'application/pdf'),
    })
    assert response.status_code == 201
    declaration_id = response.json()['declaration_id']
    current = (await client.get(f'/api/declarations/{declaration_id}')).json()
    assert current['exporter_name'] == 'Synthetic Exporter'
    assert current['buyer_name'] == 'Synthetic Buyer'
    assert current['invoice_number'] == 'SYN-PDF-001'
    assert len(current['items']) == 1
    assert current['items'][0]['hscode'] == '1234567890'
    assert Decimal(current['total_amount']) == Decimal('25.50')
    assert Decimal(current['items'][0]['quantity']) == 2
    assert Decimal(current['items'][0]['unit_price']) == Decimal('12.75')
    assert (await client.get(f'/api/declarations/{declaration_id}/export-xml')).status_code == 400
    review = await client.put(f'/api/declarations/{declaration_id}', json={'buyer_country_code': 'US'})
    assert review.status_code == 200
    validation = await client.post(f'/api/declarations/{declaration_id}/validate')
    assert validation.json() == {'valid': True, 'errors': []}
    for path in ['export-xml', 'export-file?fmt=csv', 'export-file?fmt=xlsx']:
        exported = await client.get(f'/api/declarations/{declaration_id}/{path}')
        assert exported.status_code == 200
        assert exported.content
        if path == 'export-xml':
            assert etree.fromstring(exported.content).tag.endswith('Declaration')
