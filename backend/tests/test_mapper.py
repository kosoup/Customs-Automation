from datetime import date
from decimal import Decimal

from app.services.mapper import map_to_declaration
from app.services.parser.base import ParsedInvoice, ParsedItem


def test_map_to_declaration_normalizes_invoice_fields() -> None:
    parsed = ParsedInvoice(
        exporter_name="테스트 수출자",
        buyer_name="Test Buyer",
        buyer_country_code="United States",
        invoice_number="INV-001",
        invoice_date="2026/07/12",
        incoterms="FOB Busan",
        currency_code="usd 1,000",
        total_amount=Decimal("25.50"),
        destination_country_code="japan",
        net_weight_kg=Decimal("9.25"),
        gross_weight_kg=Decimal("10.00"),
        items=[
            ParsedItem(
                item_seq=1,
                product_name_en="Widget",
                hscode="1234567890",
                quantity=Decimal("2"),
                unit="EA",
                unit_price=Decimal("12.75"),
                amount=Decimal("25.50"),
            )
        ],
    )

    result = map_to_declaration(parsed)

    assert result["buyer_country_code"] == "US"
    assert result["destination_country_code"] == "JP"
    assert result["invoice_date"] == date(2026, 7, 12)
    assert result["incoterms"] == "FOB"
    assert result["currency_code"] == "USD"
    assert result["total_amount"] == 25.5
    assert result["items"] == [
        {
            "item_seq": 1,
            "product_name_ko": None,
            "product_name_en": "Widget",
            "hscode": "1234567890",
            "model_spec": None,
            "quantity": 2.0,
            "unit": "EA",
            "unit_price": 12.75,
            "amount": 25.5,
        }
    ]


def test_map_to_declaration_preserves_unknown_values_for_validation() -> None:
    parsed = ParsedInvoice(
        buyer_country_code="Unknownland",
        invoice_date="12-07-2026",
        incoterms="unknown",
        currency_code="?",
    )

    result = map_to_declaration(parsed)

    assert result["buyer_country_code"] is None
    assert result["invoice_date"] is None
    assert result["incoterms"] == "UNK"
    assert result["currency_code"] == "?"
