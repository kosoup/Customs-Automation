import re
from decimal import Decimal
from typing import List

from app.schemas.declaration import ValidationError
from app.services.constants import INCOTERMS_VALID


def validate_declaration(data: dict, items: list) -> List[ValidationError]:
    """수출신고서 필드 검증. 오류 목록 반환."""
    errors: List[ValidationError] = []

    # 필수 필드
    required = {
        "exporter_name": "수출자명",
        "buyer_name": "구매자명",
        "buyer_country_code": "구매자 국가코드",
        "invoice_number": "인보이스 번호",
        "currency_code": "통화코드",
        "total_amount": "총금액",
    }
    for field, label in required.items():
        if not data.get(field):
            errors.append(ValidationError(field=field, message=f"{label}은(는) 필수입니다"))

    # 신고인부호: 5자리
    code = data.get("declarant_code")
    if code and len(code) != 5:
        errors.append(ValidationError(field="declarant_code", message="신고인부호는 5자리여야 합니다"))

    # 국가코드: 2자리 영문 대문자
    for field, label in [("buyer_country_code", "구매자 국가코드"), ("destination_country_code", "목적국 코드")]:
        val = data.get(field)
        if val and not re.match(r"^[A-Z]{2}$", val):
            errors.append(ValidationError(field=field, message=f"{label}는 2자리 영문 대문자여야 합니다"))

    # 통화코드: 3자리 영문 대문자
    currency = data.get("currency_code")
    if currency and not re.match(r"^[A-Z]{3}$", currency):
        errors.append(ValidationError(field="currency_code", message="통화코드는 3자리 영문 대문자여야 합니다"))

    # 인코텀스
    incoterms = data.get("incoterms")
    if incoterms and incoterms.upper() not in INCOTERMS_VALID:
        errors.append(ValidationError(field="incoterms", message=f"유효하지 않은 인코텀스: {incoterms}"))

    # 중량: 순중량 <= 총중량
    net = data.get("net_weight_kg")
    gross = data.get("gross_weight_kg")
    if net is not None and gross is not None:
        if Decimal(str(net)) > Decimal(str(gross)):
            errors.append(ValidationError(field="net_weight_kg", message="순중량이 총중량보다 클 수 없습니다"))

    # 품목 검증
    if not items:
        errors.append(ValidationError(field="items", message="품목이 최소 1건 이상이어야 합니다"))

    item_total = Decimal("0")
    for i, item in enumerate(items):
        prefix = f"items[{i}]"

        # HS코드: 10자리 숫자
        hs = item.get("hscode")
        if hs and not re.match(r"^\d{10}$", hs):
            errors.append(ValidationError(field=f"{prefix}.hscode", message="HS코드는 10자리 숫자여야 합니다"))

        # 품명 필수
        if not item.get("product_name_ko") and not item.get("product_name_en"):
            errors.append(ValidationError(field=f"{prefix}.product_name", message="품명(한글 또는 영문)은 필수입니다"))

        # 수량, 단가 > 0
        qty = item.get("quantity")
        if qty is not None and Decimal(str(qty)) <= 0:
            errors.append(ValidationError(field=f"{prefix}.quantity", message="수량은 0보다 커야 합니다"))

        price = item.get("unit_price")
        if price is not None and Decimal(str(price)) < 0:
            errors.append(ValidationError(field=f"{prefix}.unit_price", message="단가는 0 이상이어야 합니다"))

        amt = item.get("amount")
        if amt is not None:
            item_total += Decimal(str(amt))

    # 품목 금액 합계 vs 총금액
    total = data.get("total_amount")
    if total is not None and item_total > 0:
        if abs(Decimal(str(total)) - item_total) > Decimal("0.01"):
            errors.append(ValidationError(
                field="total_amount",
                message=f"총금액({total})과 품목 합계({item_total})가 일치하지 않습니다"
            ))

    return errors
