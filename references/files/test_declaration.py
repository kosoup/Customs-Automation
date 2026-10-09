"""
수출신고 API 통합 테스트
pytest + httpx 기반
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.xml_builder import build_xml
from app.services.validator import validate_xml


# ── 테스트 픽스처 ─────────────────────────────────────────────────────────────

SAMPLE_REQUEST = {
    "declaration_office_id": "01001",
    "declaration_id":        "20241108001",
    "issue_date":            "20241108",
    "invoice_amount":        "150000",
    "total_gross_mass":      "2.5",
    "total_package_quantity": 3,
    "rate_numeric":          "1330",
    "process_type_code":     "01",
    "transaction_nature_code": "01",
    "transport_type_code":   "02",
    "order_id":              "ORD-2024-0001",
    "delivery_id":           "TRACK-12345",
    "adjustment_amount":     "0",
    "currency_id":           "KRW",
    "value_amount":          "150000",
    "freight_charge":        "5000",
    "condition_code":        "DAP",
    "settlement_code":       "01",
    "loading_location":      "KRICN",
    "goods_location_id":     "04377",
    "goods_location_address": "서울시 용산구 한강대로 23길 55",
    "destination_country":   "JPN",
    "warehouse_name":        "인천국제공항 보세창고",
    "webpage_url":           "https://example.com/shop",
    "statement_description": "테스트 신고",
    "exporter": {
        "biz_number":   "1234567890",
        "customs_code": "123456789012345",
        "kts_code":     "00001",
        "name":         "테스트 수출(주)",
        "role_code":    "01",
        "representative_name": "홍길동",
        "address": {
            "country_sub_division_id": "1168010100",
            "line":         "102동 501호",
            "postcode_id":  "04377",
            "building_number": "1168010100-00001",
            "description":  "서울특별시 용산구 한강대로 23길 55",
        },
    },
    "declarant": {
        "id":   "12345678901234",
        "name": "관세사무소 테스트",
        "statement_code": "VC000000000001",
    },
    "agent": {
        "customs_code": "999999999999999",
        "kts_code":     "99999",
        "name":         "테스트 대행사",
    },
    "submitter": {
        "id":        "9999999999",
        "name":      "테스트 제출자",
        "role_code": "02",
    },
    "buyer": {"name": "Test Buyer Co., Ltd."},
    "express_id": "123456",
    "goods_items": [
        {
            "sequence_numeric":    1,
            "customs_value_amount": "50000",
            "exporter_type_code":  "C",
            "hs_code":             "6109100010",
            "description":         "면 티셔츠",
            "count_quantity":      10,
            "value_amount":        "0",
            "net_weight":          "1.2",
            "draw_back": {"role_code": "01", "application_type_code": "AD"},
            "manufacturer": {
                "biz_number":   "9876543210",
                "kts_code":     "00001",
                "customs_code": "987654321098765",
                "name":         "테스트 제조사",
            },
            "detailed_commodities": [
                {
                    "sequence_numeric":  1,
                    "cargo_description": "WHITE / M",
                    "count_quantity":    5,
                    "unit_price_amount": "5000",
                    "value_amount":      "25000",
                },
                {
                    "sequence_numeric":  2,
                    "cargo_description": "BLACK / L",
                    "count_quantity":    5,
                    "unit_price_amount": "5000",
                    "value_amount":      "25000",
                },
            ],
        },
        {
            "sequence_numeric":    2,
            "customs_value_amount": "100000",
            "exporter_type_code":  "T",
            "hs_code":             "8517120000",
            "description":         "스마트폰 케이스",
            "count_quantity":      20,
            "net_weight":          "0.5",
            "draw_back": {"role_code": "02", "application_type_code": "MN"},
            "detailed_commodities": [],
        },
    ],
}


# ── XML 생성 테스트 ───────────────────────────────────────────────────────────

def test_build_xml_success():
    from app.models.declaration import DeclarationRequest
    req = DeclarationRequest(**SAMPLE_REQUEST)
    xml_bytes = build_xml(req)
    assert xml_bytes.startswith(b"<?xml")
    assert b"Declaration" in xml_bytes
    assert b"GovernmentAgencyGoodsItem" in xml_bytes
    print(f"\nXML 생성 성공: {len(xml_bytes):,} bytes")


def test_build_xml_contains_hs_code():
    from app.models.declaration import DeclarationRequest
    req = DeclarationRequest(**SAMPLE_REQUEST)
    xml_bytes = build_xml(req)
    assert b"6109100010" in xml_bytes
    assert b"8517120000" in xml_bytes


# ── 유효성 검증 테스트 ────────────────────────────────────────────────────────

def test_validate_xml_valid():
    from app.models.declaration import DeclarationRequest
    req = DeclarationRequest(**SAMPLE_REQUEST)
    xml_bytes = build_xml(req)
    is_valid, errors = validate_xml(xml_bytes)
    assert is_valid, f"검증 실패: {errors}"


def test_validate_xml_missing_field():
    """실제 XSD 없이 수동 검증으로 필수 필드 누락 감지"""
    from app.services.validator import _manual_validate
    from lxml import etree
    invalid_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<wco:Declaration xmlns:wco="urn:kr:gov:kcs:data:standard:KCS_DeclarationOfEXP_DJPSchemaModule:1:0">
</wco:Declaration>"""
    root = etree.fromstring(invalid_xml)
    is_valid, errors = _manual_validate(root)
    assert not is_valid
    assert len(errors) > 0
    print(f"\n예상 검증 실패 메시지: {errors}")


# ── Pydantic 모델 검증 테스트 ─────────────────────────────────────────────────

def test_pydantic_invalid_hs_code():
    import copy
    from pydantic import ValidationError
    from app.models.declaration import DeclarationRequest
    bad = copy.deepcopy(SAMPLE_REQUEST)
    bad["goods_items"][0]["hs_code"] = "ABCDE"  # 숫자 아님
    with pytest.raises(ValidationError):
        DeclarationRequest(**bad)


def test_pydantic_invalid_sequence():
    import copy
    from pydantic import ValidationError
    from app.models.declaration import DeclarationRequest
    bad = copy.deepcopy(SAMPLE_REQUEST)
    bad["goods_items"][0]["sequence_numeric"] = 5  # 연속 아님 (1이어야 함)
    with pytest.raises(ValidationError):
        DeclarationRequest(**bad)


def test_pydantic_too_many_goods_items():
    import copy
    from pydantic import ValidationError
    from app.models.declaration import DeclarationRequest
    bad = copy.deepcopy(SAMPLE_REQUEST)
    # 1000개 란 (최대 999)
    bad["goods_items"] = [
        {**bad["goods_items"][0], "sequence_numeric": i}
        for i in range(1, 1001)
    ]
    with pytest.raises(ValidationError):
        DeclarationRequest(**bad)


# ── API 엔드포인트 테스트 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_api_preview_xml():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/declaration/xml", json=SAMPLE_REQUEST)
    assert resp.status_code == 200
    assert "xml" in resp.headers["content-type"]
    assert b"Declaration" in resp.content


@pytest.mark.asyncio
async def test_api_validate_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/declaration/validate", json=SAMPLE_REQUEST)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["error_count"] == 0


@pytest.mark.asyncio
async def test_api_submit_mock():
    """Mock 모드에서 전송 테스트"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/declaration/submit", json=SAMPLE_REQUEST)
    assert resp.status_code == 200
    data = resp.json()
    print(f"\nMock 전송 결과: {data}")
    # Mock 모드이므로 success=True가 높은 확률로 반환됨


@pytest.mark.asyncio
async def test_api_full_flow():
    """전체 흐름 테스트 (서명 없이)"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/declaration/full", json=SAMPLE_REQUEST)
    assert resp.status_code == 200
    data = resp.json()
    print(f"\n전체 흐름 결과: success={data['success']}, msg={data['message']}")


@pytest.mark.asyncio
async def test_api_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/declaration/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    print(f"\n헬스체크: {data}")
