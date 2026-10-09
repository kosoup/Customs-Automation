import io

import openpyxl

from app.models.declaration import Declaration, DeclarationItem
from app.services.submission import file_export


def _make_declaration() -> Declaration:
    decl = Declaration(
        exporter_name='=HYPERLINK("http://evil.example/?x","click")',
        buyer_name="+cmd|'/c calc'!A1",
        total_amount=-500,
    )
    decl.items.append(
        DeclarationItem(
            item_seq=1,
            product_name_en="@SUM(A1:A10)",
            product_name_ko="정상 품명",
        )
    )
    return decl


def test_generate_csv_escapes_formula_prefixed_fields():
    csv_bytes = file_export.generate_csv(_make_declaration())
    text = csv_bytes.decode("utf-8-sig")

    assert "'=HYPERLINK" in text
    assert "'+cmd" in text
    assert "'@SUM(A1:A10)" in text
    # A normal value must not be mangled.
    assert "정상 품명" in text


def test_generate_excel_escapes_formula_prefixed_cells():
    xlsx_bytes = file_export.generate_excel(_make_declaration())
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb.active

    values = [cell.value for row in ws.iter_rows() for cell in row if cell.value is not None]
    assert any(isinstance(v, str) and v.startswith("'=HYPERLINK") for v in values)
    assert any(isinstance(v, str) and v.startswith("'@SUM") for v in values)
