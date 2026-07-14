from app.services.validator import validate_declaration


def _valid_declaration() -> tuple[dict, list[dict]]:
    data = {
        "declarant_code": "A1234",
        "exporter_name": "테스트 수출자",
        "buyer_name": "Test Buyer",
        "buyer_country_code": "US",
        "destination_country_code": "US",
        "invoice_number": "INV-001",
        "currency_code": "USD",
        "incoterms": "FOB",
        "total_amount": "30.00",
        "net_weight_kg": "9.5",
        "gross_weight_kg": "10",
    }
    items = [
        {
            "hscode": "1234567890",
            "product_name_en": "Widget",
            "quantity": "2",
            "unit_price": "10",
            "amount": "20.00",
        },
        {
            "hscode": "0987654321",
            "product_name_ko": "부품",
            "quantity": "1",
            "unit_price": "10",
            "amount": "10.00",
        },
    ]
    return data, items


def test_valid_declaration_has_no_errors() -> None:
    data, items = _valid_declaration()

    assert validate_declaration(data, items) == []


def test_required_fields_and_items_are_reported() -> None:
    errors = validate_declaration({}, [])

    fields = {error.field for error in errors}
    assert {
        "exporter_name",
        "buyer_name",
        "buyer_country_code",
        "invoice_number",
        "currency_code",
        "total_amount",
        "items",
    } <= fields


def test_invalid_codes_weights_and_item_values_are_reported() -> None:
    data, items = _valid_declaration()
    data.update(
        {
            "declarant_code": "1234",
            "buyer_country_code": "usa",
            "destination_country_code": "USA",
            "currency_code": "usd",
            "incoterms": "INVALID",
            "net_weight_kg": "11",
        }
    )
    items[0].update(
        {
            "hscode": "1234",
            "product_name_en": None,
            "quantity": "0",
            "unit_price": "-1",
        }
    )

    errors = validate_declaration(data, items)
    fields = {error.field for error in errors}

    assert {
        "declarant_code",
        "buyer_country_code",
        "destination_country_code",
        "currency_code",
        "incoterms",
        "net_weight_kg",
        "items[0].hscode",
        "items[0].product_name",
        "items[0].quantity",
        "items[0].unit_price",
    } <= fields


def test_item_total_must_match_declaration_total() -> None:
    data, items = _valid_declaration()
    data["total_amount"] = "31.00"

    errors = validate_declaration(data, items)

    assert any(error.field == "total_amount" for error in errors)
