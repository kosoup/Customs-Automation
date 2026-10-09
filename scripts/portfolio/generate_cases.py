"""Generate two explicitly synthetic image-only evaluation PDFs.

Optional authoring dependencies: reportlab, pypdfium2, Pillow.
Existing DEMO-001 is preserved as the baseline.
"""
import io
import json
from pathlib import Path

import pypdfium2 as pdfium
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/pdf'
DATA = ROOT / 'docs/demo-cases'


def generate(case_id: str, alternate: bool) -> None:
    buyer = 'DEMO GEAR IMPORTS' if not alternate else 'DEMO CRAFT IMPORTS'
    manufacturer = 'DEMO GEAR WORKS' if not alternate else 'DEMO CRAFT WORKS'
    currency, country = ('EUR', 'DE') if not alternate else ('USD', 'CA')
    profile = {'환급신청인': '2', '간이자동정액환급여부': 'NO',
               '구매자코드': f'{case_id}-BUYER', '거래구분': '11'}
    common = dict(profile, **{'목적국': country, '구매자': buyer, '제조자': manufacturer,
        '결제방법': 'TT', '인도조건': 'FCA', '통화단위': currency,
        '운임비': '0.00', '기타금액': '0.00', '총금액': '60.00',
        '총중량': '8.00', '전체순중량': '6.00', '카톤수': '2'})
    items = []
    for i in range(1, 4):
        items.append({'규격1': f'Assembly PN-{case_id}-{i:03}', '규격2': '', '규격3': '',
            '수량': str(i * 2), '단가': '5.00', '금액': f'{i * 10:.2f}',
            'FTA발급여부': 'Y' if not alternate else 'N',
            'FTA발급협정코드': '106' if not alternate else '',
            '세번부호': '9503000000', '품명': 'PARTS OF TOYS',
            '거래품명': 'TOY COMPONENTS', '순중량': ''})
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(595, 842))
    c.setTitle(f'{case_id} - SYNTHETIC - NOT FOR FILING')
    c.setFillColorRGB(.08, .2, .3)
    c.rect(35, 746, 525, 60, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont('Helvetica-Bold', 16)
    c.drawString(48, 780, 'COMMERCIAL INVOICE / PACKING SUMMARY')
    c.setFont('Helvetica', 10)
    c.drawString(48, 760, f'{case_id} | SYNTHETIC ONLY - NOT FOR CUSTOMS FILING')
    c.setFillColorRGB(0, 0, 0)
    fields = [
        f"{'Consignee' if alternate else 'Buyer'}: {buyer}",
        f"Manufacturer: {manufacturer}",
        f"{'Ship to' if alternate else 'Destination'}: {'Canada' if alternate else 'Germany'} ({country})",
        'Terms: FCA', f'Currency: {currency}', 'Payment: T/T',
        f"FTA preference requested: {'NO' if alternate else 'YES'}",
        'HS code: 9503000000', 'Goods: PARTS OF TOYS | Trade name: TOY COMPONENTS',
        'Origin: KR']
    if not alternate:
        fields.insert(7, 'FTA agreement code: 106')
    c.setFont('Helvetica', 11)
    for i, value in enumerate(fields):
        c.drawString(48, 718 - 22 * i, value)
    # Reordered columns in case 2; unfamiliar headings in case 3.
    headers = ['Description', 'Amount', 'Qty', 'Unit'] if not alternate else ['Product details', 'Quantity', 'Price', 'Line total']
    xs = [48, 344, 425, 495] if not alternate else [48, 336, 414, 486]
    c.setFillColorRGB(.91, .94, .97)
    c.rect(40, 414, 515, 28, fill=1, stroke=0)
    c.setFillColorRGB(0, 0, 0)
    c.setFont('Helvetica-Bold', 11)
    for x, label in zip(xs, headers):
        c.drawString(x, 424, label)
    c.setFont('Helvetica', 10)
    for i, item in enumerate(items):
        y = 386 - i * 40
        values = [item['규격1'], item['금액'], item['수량'], item['단가']] if not alternate else [item['규격1'], item['수량'], item['단가'], item['금액']]
        for x, value in zip(xs, values):
            c.drawString(x, y, value)
        c.setStrokeColorRGB(.7, .75, .8)
        c.line(40, y - 12, 555, y - 12)
    c.setFont('Helvetica', 11)
    for i, value in enumerate([f"{'Invoice value' if alternate else 'Total amount'}: {currency} 60.00",
        f'Freight: {currency} 0.00', f'Other charges: {currency} 0.00',
        'Gross weight: 8.00 KG', 'Total net weight: 6.00 KG', 'Packages: 2 cartons']):
        c.drawString(48, 262 - 23 * i, value)
    c.setFont('Helvetica', 8)
    c.drawString(48, 70, 'All parties, codes and values are fictional. HS/FTA codes are test values, not legal advice.')
    c.drawString(48, 56, 'Item net weights and customs origin codes are intentionally unspecified. Page 1 of 1')
    c.save()
    document = pdfium.PdfDocument(buffer.getvalue())
    page = document[0]
    bitmap = page.render(scale=2)
    raster = bitmap.to_pil().convert('RGB')
    final = canvas.Canvas(str(OUT / f'{case_id}.pdf'), pagesize=(595, 842))
    final.drawImage(ImageReader(raster), 0, 0, width=595, height=842)
    final.save()
    bitmap.close()
    page.close()
    document.close()
    (DATA / f'{case_id}-expected.json').write_text(json.dumps({
        'case': case_id, 'synthetic': True, 'profile': profile, 'common': common,
        'items': items, 'description': 'Alternative labels and unsupported table' if alternate else 'Boxed summary and reordered table columns',
        'review_required': 'Origin customs code is unknown; do not mark filing ready.'
    }, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    generate('DEMO-002', False)
    generate('DEMO-003', True)
