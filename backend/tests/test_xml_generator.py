from __future__ import annotations

from datetime import date
from decimal import Decimal

from lxml import etree

from app.models.company_settings import CompanySettings
from app.models.declaration import Declaration, DeclarationItem
from app.services.xml_generator import NS, generate_govcbr830_xml


def _text(root: etree._Element, path: str) -> str | None:
    node = root.find(path, {"wco": NS})
    return node.text if node is not None else None


def test_xml_preserves_decimal_values_and_item_structure() -> None:
    declaration = Declaration(
        declarant_code="A1234",
        declarant_name="테스트 신고인",
        exporter_name="테스트 수출자",
        exporter_business_number="123-45-67890",
        exporter_address="부산광역시",
        buyer_name="Test Buyer",
        buyer_country_code="US",
        invoice_number="INV-XML-001",
        currency_code="USD",
        incoterms="FOB",
        loading_port="KRPUS",
        shipping_date=date(2026, 7, 13),
        total_amount=Decimal("25.50"),
        gross_weight_kg=Decimal("10.250"),
        package_type="CT",
        package_count=1,
    )
    declaration.items = [
        DeclarationItem(
            item_seq=1,
            product_name_en="Widget",
            hscode="1234567890",
            model_spec="W-1",
            quantity=Decimal("2.500"),
            unit="EA",
            unit_price=Decimal("10.20"),
            amount=Decimal("25.50"),
        )
    ]

    root = etree.fromstring(generate_govcbr830_xml(declaration))

    assert root.tag == f"{{{NS}}}Declaration"
    assert _text(root, "wco:GoodsItemQuantity") == "1"
    assert _text(root, "wco:InvoiceAmount") == "25.50"
    assert _text(root, "wco:TotalGrossMassMeasure") == "10.250"
    assert _text(root, ".//wco:GovernmentAgencyGoodsItem/wco:SequenceNumeric") == "001"
    assert _text(root, ".//wco:Commodity/wco:CountQuantity") == "2.500"
    assert _text(root, ".//wco:DetailedCommodity/wco:UnitPriceAmount") == "10.20"
    assert _text(root, ".//wco:Classification/wco:ID") == "1234567890"


def test_company_settings_override_exporter_and_submitter_fields() -> None:
    declaration = Declaration(
        declarant_code="OLD01",
        declarant_name="기존 신고인",
        exporter_name="테스트 수출자",
        exporter_business_number="old-business-number",
        exporter_address="기존 주소",
        buyer_name="Test Buyer",
        buyer_country_code="US",
        invoice_number="INV-XML-002",
        items=[],
    )
    company = CompanySettings(
        id=1,
        declarant_code="NEW01",
        declarant_name="설정 신고인",
        representative_name="대표자",
        exporter_business_number="new-business-number",
        exporter_customs_id="CUSTOMS-ID",
        exporter_address="설정 주소",
        exporter_postcode="12345",
        loading_port="KRINC",
        customs_office="010",
    )

    root = etree.fromstring(generate_govcbr830_xml(declaration, company))

    assert _text(root, "wco:DeclarationOfficeID") == "010"
    assert _text(root, ".//wco:Exporter/wco:Address/wco:Line") == "설정 주소"
    assert _text(root, ".//wco:LoadingLocation/wco:ID") == "KRINC"
    assert _text(root, ".//wco:Submitter/wco:ID") == "NEW01"
    assert _text(root, ".//wco:Submitter/wco:Name") == "설정 신고인"
