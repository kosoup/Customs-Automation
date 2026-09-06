import re
from decimal import Decimal, InvalidOperation
from typing import Optional

import pdfplumber

from ..constants import INCOTERMS_VALID
from .base import BaseParser, ParsedInvoice, ParsedItem


def _to_decimal(val) -> Optional[Decimal]:
    if val is None:
        return None
    clean = re.sub(r"[^\d.]", "", str(val))
    if not clean:
        return None
    try:
        return Decimal(clean).quantize(Decimal("0.0001"))
    except InvalidOperation:
        return None


def _extract_date(text: str) -> Optional[str]:
    m = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", text)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})", text)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return None


def _extract_incoterms(text: str) -> Optional[str]:
    for term in INCOTERMS_VALID:
        if re.search(rf"\b{term}\b", text.upper()):
            return term
    return None


def _extract_currency(text: str) -> Optional[str]:
    m = re.search(r"\b(USD|EUR|JPY|GBP|CNY|KRW|SGD|AUD|CAD)\b", text.upper())
    return m.group(1) if m else None


def _search_pattern(lines: list, pattern: str, group: int = 1) -> Optional[str]:
    """여러 줄에서 정규식 패턴으로 값을 추출."""
    for line in lines:
        m = re.search(pattern, line, re.IGNORECASE)
        if m:
            return m.group(group).strip()
    return None


class PdfParser(BaseParser):

    def parse(self, file_path: str, template: Optional[dict] = None) -> ParsedInvoice:
        result = ParsedInvoice()
        tpl = template or {}
        headers = tpl.get("item_table_headers", {
            "product_name_en": ["description", "item", "goods", "product", "commodity"],
            "hscode": ["hs code", "hs-code", "hscode", "tariff"],
            "quantity": ["qty", "quantity"],
            "unit": ["unit", "uom"],
            "unit_price": ["unit price", "price", "rate"],
            "amount": ["amount", "total", "value"],
        })

        all_text_lines = []
        all_tables = []

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                all_text_lines.extend(text.splitlines())

                # 테이블 추출
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)

        # 1. 텍스트에서 메타 정보 추출
        full_text = "\n".join(all_text_lines)

        # 인보이스 번호
        result.invoice_number = _search_pattern(
            all_text_lines,
            r"(?:invoice\s*(?:no\.?|number|#)[:\s]*)([\w\-/]+)",
        )

        # 인보이스 날짜
        raw_date = _search_pattern(
            all_text_lines,
            r"(?:invoice\s*date|date)[:\s]*([\d]{4}[./-][\d]{1,2}[./-][\d]{1,2}|[\d]{1,2}[./-][\d]{1,2}[./-][\d]{4})",
        )
        if raw_date:
            result.invoice_date = _extract_date(raw_date) or raw_date

        # 인코텀스
        result.incoterms = _extract_incoterms(full_text)

        # 통화
        result.currency_code = _extract_currency(full_text)

        # 총액
        raw_total = _search_pattern(
            all_text_lines,
            r"(?:grand\s*total|total\s*amount|total)[:\s]*([\d,]+\.?\d*)",
        )
        result.total_amount = _to_decimal(raw_total)

        # 수출자 (Seller / Shipper / Exporter 키워드 다음 줄)
        for i, line in enumerate(all_text_lines):
            if re.search(r"^\s*(seller|shipper|exporter|from)\b", line, re.IGNORECASE):
                # 같은 줄에 값이 있으면 사용, 없으면 다음 줄
                after = re.sub(r"^\s*(?:seller|shipper|exporter|from)\b", "", line, count=1, flags=re.IGNORECASE).strip(" :/")
                if after:
                    result.exporter_name = after
                elif i + 1 < len(all_text_lines):
                    result.exporter_name = all_text_lines[i + 1].strip()
                break

        # 구매자
        for i, line in enumerate(all_text_lines):
            if re.search(r"^\s*(buyer|consignee|importer|to)\b", line, re.IGNORECASE):
                after = re.sub(r"^\s*(?:buyer|consignee|importer|to)\b", "", line, count=1, flags=re.IGNORECASE).strip(" :/")
                if after:
                    result.buyer_name = after
                elif i + 1 < len(all_text_lines):
                    result.buyer_name = all_text_lines[i + 1].strip()
                break

        # 2. 테이블에서 품목 추출
        for table in all_tables:
            if not table or len(table) < 2:
                continue

            # 헤더 행 탐색
            col_map = {}
            header_idx = None
            for r_idx, row in enumerate(table):
                matched = {}
                for c_idx, cell in enumerate(row):
                    if cell is None:
                        continue
                    cell_lower = str(cell).lower().strip()
                    for field_name, kws in headers.items():
                        if field_name not in matched and any(kw in cell_lower for kw in kws):
                            matched[field_name] = c_idx
                if len(matched) >= 3:
                    col_map = matched
                    header_idx = r_idx
                    break

            if header_idx is None:
                continue

            seq = len(result.items) + 1
            for row in table[header_idx + 1:]:
                def get(field):
                    idx = col_map.get(field)
                    if idx is not None and idx < len(row):
                        v = row[idx]
                        return str(v).strip() if v else None
                    return None

                qty = _to_decimal(get("quantity"))
                if qty is None or qty <= 0:
                    continue

                hs_raw = get("hscode") or ""
                item = ParsedItem(
                    item_seq=seq,
                    product_name_en=get("product_name_en"),
                    hscode=re.sub(r"[^\d]", "", hs_raw) or None,
                    model_spec=get("model_spec"),
                    quantity=qty,
                    unit=get("unit"),
                    unit_price=_to_decimal(get("unit_price")),
                    amount=_to_decimal(get("amount")),
                )
                result.items.append(item)
                seq += 1

        # total_amount 없으면 품목 합계
        if result.total_amount is None and result.items:
            s = sum(i.amount for i in result.items if i.amount)
            if s:
                result.total_amount = s

        return result
