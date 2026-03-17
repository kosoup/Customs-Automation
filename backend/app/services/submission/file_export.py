"""
UNI-PASS 웹 업로드용 수출신고서 파일 생성.
관세청 간이수출신고 엑셀 양식(최대 100건) 기준으로 생성한다.
"""
import csv
import io
from pathlib import Path
from typing import List

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from app.models.declaration import Declaration, DeclarationItem


def _val(v) -> str:
    if v is None:
        return ""
    return str(v)


def generate_csv(declaration: Declaration) -> bytes:
    """신고서 데이터를 CSV로 직렬화 (간단한 범용 포맷)."""
    output = io.StringIO()
    writer = csv.writer(output)

    # 헤더
    writer.writerow([
        "신고인부호", "수출자명", "사업자번호", "수출자주소",
        "구매자명", "구매자국가", "구매자주소",
        "인코텀스", "통화", "결제방식",
        "인보이스번호", "인보이스일자", "총금액",
        "적재항", "목적국", "목적항", "선적일",
        "순중량(kg)", "총중량(kg)", "포장종류", "포장개수",
    ])

    writer.writerow([
        _val(declaration.declarant_code),
        _val(declaration.exporter_name),
        _val(declaration.exporter_business_number),
        _val(declaration.exporter_address),
        _val(declaration.buyer_name),
        _val(declaration.buyer_country_code),
        _val(declaration.buyer_address),
        _val(declaration.incoterms),
        _val(declaration.currency_code),
        _val(declaration.payment_method),
        _val(declaration.invoice_number),
        _val(declaration.invoice_date),
        _val(declaration.total_amount),
        _val(declaration.loading_port),
        _val(declaration.destination_country_code),
        _val(declaration.destination_port),
        _val(declaration.shipping_date),
        _val(declaration.net_weight_kg),
        _val(declaration.gross_weight_kg),
        _val(declaration.package_type),
        _val(declaration.package_count),
    ])

    writer.writerow([])
    writer.writerow(["란번호", "품명(한글)", "품명(영문)", "HS코드", "규격", "수량", "단위", "단가", "금액"])

    for item in sorted(declaration.items, key=lambda i: i.item_seq):
        writer.writerow([
            _val(item.item_seq),
            _val(item.product_name_ko),
            _val(item.product_name_en),
            _val(item.hscode),
            _val(item.model_spec),
            _val(item.quantity),
            _val(item.unit),
            _val(item.unit_price),
            _val(item.amount),
        ])

    return output.getvalue().encode("utf-8-sig")  # BOM 포함 (Excel 호환)


def generate_excel(declaration: Declaration) -> bytes:
    """수출신고서를 서식화된 Excel 파일로 생성."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "수출신고서"

    # 스타일 정의
    header_font = Font(bold=True, size=11)
    header_fill = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
    center = Alignment(horizontal="center", vertical="center")
    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    def hcell(row, col, value, width=None):
        c = ws.cell(row=row, column=col, value=value)
        c.font = header_font
        c.fill = header_fill
        c.alignment = center
        c.border = border
        if width:
            ws.column_dimensions[c.column_letter].width = width
        return c

    def dcell(row, col, value):
        c = ws.cell(row=row, column=col, value=value)
        c.alignment = Alignment(vertical="center", wrap_text=True)
        c.border = border
        return c

    # 제목
    ws.merge_cells("A1:U1")
    title = ws["A1"]
    title.value = "수출신고서 (수출 통관용)"
    title.font = Font(bold=True, size=14)
    title.alignment = center
    ws.row_dimensions[1].height = 30

    # 기본 정보 섹션
    r = 3
    meta_fields = [
        ("신고인부호", declaration.declarant_code),
        ("신고인명", declaration.declarant_name),
        ("수출자명", declaration.exporter_name),
        ("사업자등록번호", declaration.exporter_business_number),
        ("수출자주소", declaration.exporter_address),
        ("구매자명", declaration.buyer_name),
        ("구매자 국가코드", declaration.buyer_country_code),
        ("구매자 주소", declaration.buyer_address),
        ("인코텀스", declaration.incoterms),
        ("통화", declaration.currency_code),
        ("결제방식", declaration.payment_method),
        ("인보이스번호", declaration.invoice_number),
        ("인보이스일자", str(declaration.invoice_date) if declaration.invoice_date else ""),
        ("총금액", declaration.total_amount),
        ("적재항", declaration.loading_port),
        ("목적국", declaration.destination_country_code),
        ("목적항", declaration.destination_port),
        ("선적일", str(declaration.shipping_date) if declaration.shipping_date else ""),
        ("순중량(kg)", declaration.net_weight_kg),
        ("총중량(kg)", declaration.gross_weight_kg),
        ("포장종류", declaration.package_type),
        ("포장개수", declaration.package_count),
    ]

    for i, (label, value) in enumerate(meta_fields):
        row = r + (i // 2)
        col_label = 1 + (i % 2) * 2
        col_value = col_label + 1
        hcell(row, col_label, label, width=18)
        dcell(row, col_value, value)

    # 품목 테이블 헤더
    item_start_row = r + (len(meta_fields) + 1) // 2 + 2
    item_headers = ["란번호", "품명(한글)", "품명(영문)", "HS코드", "규격", "수량", "단위", "단가", "금액"]
    col_widths = [8, 20, 20, 14, 16, 10, 8, 12, 12]
    for ci, (h, w) in enumerate(zip(item_headers, col_widths), start=1):
        hcell(item_start_row, ci, h, width=w)

    for item in sorted(declaration.items, key=lambda i: i.item_seq):
        row = item_start_row + item.item_seq
        dcell(row, 1, item.item_seq)
        dcell(row, 2, item.product_name_ko)
        dcell(row, 3, item.product_name_en)
        dcell(row, 4, item.hscode)
        dcell(row, 5, item.model_spec)
        dcell(row, 6, float(item.quantity) if item.quantity else None)
        dcell(row, 7, item.unit)
        dcell(row, 8, float(item.unit_price) if item.unit_price else None)
        dcell(row, 9, float(item.amount) if item.amount else None)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
