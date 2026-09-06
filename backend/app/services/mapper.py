"""ParsedInvoice → Declaration/DeclarationItem 딕셔너리 변환."""

import re
from datetime import date
from typing import Optional

from .constants import INCOTERMS_VALID
from .parser.base import ParsedInvoice

# 주요 국가명 → ISO 2자리 코드
COUNTRY_MAP = {
    "united states": "US", "usa": "US", "us": "US",
    "china": "CN", "prc": "CN",
    "japan": "JP",
    "germany": "DE",
    "france": "FR",
    "united kingdom": "GB", "uk": "GB",
    "australia": "AU",
    "canada": "CA",
    "singapore": "SG",
    "vietnam": "VN", "viet nam": "VN",
    "korea": "KR", "south korea": "KR",
    "taiwan": "TW",
    "india": "IN",
    "indonesia": "ID",
    "thailand": "TH",
    "malaysia": "MY",
    "philippines": "PH",
    "hong kong": "HK",
}

def _parse_date(text: Optional[str]) -> Optional[date]:
    """YYYY-MM-DD 문자열을 date 객체로 변환."""
    if not text:
        return None
    try:
        parts = re.split(r"[./-]", text.strip())
        if len(parts) == 3 and len(parts[0]) == 4:
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        pass
    return None


def _normalize_country(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    text = text.strip()
    # 이미 2자리 대문자이면 그대로
    if re.match(r"^[A-Z]{2}$", text):
        return text
    return COUNTRY_MAP.get(text.lower())


def _normalize_currency(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"[A-Za-z]{3}", text)
    return m.group(0).upper() if m else None


def _normalize_incoterms(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    for term in INCOTERMS_VALID:
        if term in text.upper():
            return term
    return text.upper()[:3] if text else None


def map_to_declaration(parsed: ParsedInvoice) -> dict:
    """ParsedInvoice를 Declaration 생성용 딕셔너리로 변환."""
    items = [
        {
            "item_seq": item.item_seq,
            "product_name_ko": item.product_name_ko,
            "product_name_en": item.product_name_en,
            "hscode": item.hscode,
            "model_spec": item.model_spec,
            "quantity": float(item.quantity) if item.quantity is not None else None,
            "unit": item.unit,
            "unit_price": float(item.unit_price) if item.unit_price is not None else None,
            "amount": float(item.amount) if item.amount is not None else None,
        }
        for item in parsed.items
    ]

    return {
        "exporter_name": parsed.exporter_name,
        "exporter_address": parsed.exporter_address,
        "buyer_name": parsed.buyer_name,
        "buyer_country_code": _normalize_country(parsed.buyer_country_code),
        "buyer_address": parsed.buyer_address,
        "invoice_number": parsed.invoice_number,
        "invoice_date": _parse_date(parsed.invoice_date),
        "incoterms": _normalize_incoterms(parsed.incoterms),
        "currency_code": _normalize_currency(parsed.currency_code) or parsed.currency_code,
        "payment_method": parsed.payment_method,
        "total_amount": float(parsed.total_amount) if parsed.total_amount is not None else None,
        "loading_port": parsed.loading_port,
        "destination_country_code": _normalize_country(parsed.destination_country_code),
        "destination_port": parsed.destination_port,
        "net_weight_kg": float(parsed.net_weight_kg) if parsed.net_weight_kg is not None else None,
        "gross_weight_kg": float(parsed.gross_weight_kg) if parsed.gross_weight_kg is not None else None,
        "package_type": parsed.package_type,
        "package_count": parsed.package_count,
        "items": items,
    }
