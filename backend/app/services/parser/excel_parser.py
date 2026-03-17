import re
from decimal import Decimal, InvalidOperation
from typing import Optional

import openpyxl

from .base import BaseParser, ParsedInvoice, ParsedItem


def _to_decimal(val) -> Optional[Decimal]:
    if val is None:
        return None
    try:
        return Decimal(str(val)).quantize(Decimal("0.0001"))
    except InvalidOperation:
        return None


def _normalize(text: str) -> str:
    return str(text).lower().strip()


def _match_keywords(cell_val, keywords: list) -> bool:
    v = _normalize(str(cell_val))
    return any(kw in v for kw in keywords)


def _extract_date(text: str) -> Optional[str]:
    """다양한 날짜 형식을 YYYY-MM-DD로 변환."""
    text = str(text).strip()
    patterns = [
        (r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", "{}-{:02d}-{:02d}"),
        (r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})", None),
    ]
    m = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", text)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})", text)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return None


def _extract_incoterms(text: str) -> Optional[str]:
    valid = {"EXW", "FCA", "FAS", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP"}
    for term in valid:
        if term in text.upper():
            return term
    return None


def _extract_currency(text: str) -> Optional[str]:
    m = re.search(r"\b(USD|EUR|JPY|GBP|CNY|KRW|SGD|AUD|CAD)\b", text.upper())
    return m.group(1) if m else None


class ExcelParser(BaseParser):

    def parse(self, file_path: str, template: Optional[dict] = None) -> ParsedInvoice:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb.active

        result = ParsedInvoice()
        tpl = template or {}
        headers = tpl.get("item_table_headers", {
            "product_name_en": ["description", "item", "goods", "product", "commodity", "품명"],
            "hscode": ["hs code", "hs-code", "hscode", "tariff", "품목번호"],
            "quantity": ["qty", "quantity", "수량"],
            "unit": ["unit", "uom", "단위"],
            "unit_price": ["unit price", "price", "rate", "단가"],
            "amount": ["amount", "total", "value", "금액"],
        })

        seller_kws = tpl.get("seller_keywords", ["seller", "shipper", "exporter", "from", "수출자"])
        buyer_kws = tpl.get("buyer_keywords", ["buyer", "consignee", "importer", "to", "수입자"])
        inv_no_kws = tpl.get("invoice_number_keywords", ["invoice no", "invoice number", "inv no", "inv."])
        inv_dt_kws = tpl.get("invoice_date_keywords", ["invoice date", "date", "발행일"])
        total_kws = tpl.get("total_keywords", ["total", "grand total", "total amount", "합계", "총액"])

        rows = list(ws.iter_rows(values_only=True))

        # 1. 헤더 키-값 탐색 (상단 메타 영역)
        for r_idx, row in enumerate(rows):
            for c_idx, cell in enumerate(row):
                if cell is None:
                    continue
                cell_str = str(cell).strip()
                if not cell_str:
                    continue

                # 같은 행에서 오른쪽 셀을 값으로 사용
                def right_val(offset=1):
                    cols = list(row)
                    idx = c_idx + offset
                    while idx < len(cols):
                        v = cols[idx]
                        if v is not None and str(v).strip():
                            return str(v).strip()
                        idx += 1
                    return None

                # 다음 행에서 같은 컬럼을 값으로 사용
                def below_val():
                    if r_idx + 1 < len(rows):
                        v = rows[r_idx + 1][c_idx] if c_idx < len(rows[r_idx + 1]) else None
                        return str(v).strip() if v else None
                    return None

                if _match_keywords(cell_str, inv_no_kws) and not result.invoice_number:
                    result.invoice_number = right_val() or below_val()

                if _match_keywords(cell_str, inv_dt_kws) and not result.invoice_date:
                    raw = right_val() or below_val()
                    if raw:
                        result.invoice_date = _extract_date(raw) or raw

                if _match_keywords(cell_str, seller_kws) and not result.exporter_name:
                    result.exporter_name = right_val() or below_val()

                if _match_keywords(cell_str, buyer_kws) and not result.buyer_name:
                    result.buyer_name = right_val() or below_val()

                if _match_keywords(cell_str, ["incoterms", "terms", "delivery terms"]) and not result.incoterms:
                    raw = right_val() or below_val() or ""
                    result.incoterms = _extract_incoterms(raw) or raw.upper()[:3] or None

                if _match_keywords(cell_str, ["currency", "통화"]) and not result.currency_code:
                    raw = right_val() or below_val() or ""
                    result.currency_code = _extract_currency(raw) or (raw.upper()[:3] if raw else None)

                # 통화가 셀 값 자체에 포함된 경우 (예: "USD 5,000")
                if not result.currency_code:
                    cur = _extract_currency(cell_str)
                    if cur:
                        result.currency_code = cur

                if _match_keywords(cell_str, total_kws) and not result.total_amount:
                    raw = right_val() or below_val()
                    if raw:
                        clean = re.sub(r"[^\d.]", "", str(raw))
                        result.total_amount = _to_decimal(clean)

        # 2. 품목 테이블 탐색
        header_row_idx = None
        col_map: dict = {}

        for r_idx, row in enumerate(rows):
            matched = {}
            for c_idx, cell in enumerate(row):
                if cell is None:
                    continue
                for field_name, kws in headers.items():
                    if field_name not in matched and _match_keywords(str(cell), kws):
                        matched[field_name] = c_idx
            # 최소 3개 이상 컬럼이 매핑되면 품목 헤더 행으로 판단
            if len(matched) >= 3:
                header_row_idx = r_idx
                col_map = matched
                break

        if header_row_idx is not None:
            seq = 1
            for row in rows[header_row_idx + 1:]:
                qty_col = col_map.get("quantity")
                price_col = col_map.get("unit_price")
                amt_col = col_map.get("amount")

                # 수량이나 금액이 없는 행은 품목 행이 아님
                qty_val = row[qty_col] if qty_col is not None and qty_col < len(row) else None
                amt_val = row[amt_col] if amt_col is not None and amt_col < len(row) else None
                if not qty_val and not amt_val:
                    continue
                qty = _to_decimal(qty_val)
                if qty is None or qty <= 0:
                    continue

                def get_col(field_name):
                    idx = col_map.get(field_name)
                    if idx is not None and idx < len(row):
                        return row[idx]
                    return None

                item = ParsedItem(
                    item_seq=seq,
                    product_name_en=str(get_col("product_name_en") or "").strip() or None,
                    hscode=re.sub(r"[^\d]", "", str(get_col("hscode") or "")) or None,
                    model_spec=str(get_col("model_spec") or "").strip() or None,
                    quantity=qty,
                    unit=str(get_col("unit") or "").strip() or None,
                    unit_price=_to_decimal(get_col("unit_price")),
                    amount=_to_decimal(get_col("amount")),
                )
                result.items.append(item)
                seq += 1

        # total_amount가 없으면 품목 합계로 계산
        if result.total_amount is None and result.items:
            s = sum(i.amount for i in result.items if i.amount)
            if s:
                result.total_amount = s

        return result
