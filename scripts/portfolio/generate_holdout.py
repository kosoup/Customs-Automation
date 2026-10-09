"""Create a new synthetic two-page evaluation case after alias rules were fixed.

Uses the optional authoring dependencies reportlab, pypdfium2 and Pillow.
This is a controlled combination test, not an independent real-world sample.
"""
import io
import json
from pathlib import Path

import pypdfium2 as pdfium
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[2]


def main():
    profile = {'환급신청인': '2', '간이자동정액환급여부': 'NO',
               '구매자코드': 'DEMO-004-BUYER', '거래구분': '11'}
    common = dict(profile, **{'목적국': 'AU', '구매자': 'DEMO SOUTH IMPORTS',
        '제조자': 'DEMO SOUTH WORKS', '결제방법': 'TT', '인도조건': 'CIF',
        '통화단위': 'USD', '운임비': '0.00', '기타금액': '0.00',
        '총금액': '12,500.00', '총중량': '40.00', '전체순중량': '35.00', '카톤수': '8'})
    items = [{'규격1': f'Kit PN-HOLD-{i:03}', '규격2': '', '규격3': '',
              '수량': str(i), '단가': '1,250.00', '금액': f'{i*1250:,.2f}',
              'FTA발급여부': 'N', 'FTA발급협정코드': '', '세번부호': '9503000000',
              '품명': 'PARTS OF TOYS', '거래품명': 'TOY COMPONENTS', '순중량': ''}
             for i in range(1, 5)]
    source = io.BytesIO()
    c = canvas.Canvas(source, pagesize=(842, 595))
    for page in range(2):
        c.setFillColorRGB(.05, .2, .3)
        c.setFont('Helvetica-Bold', 18)
        c.drawString(40, 548, f'SYNTHETIC SHIPMENT / DEMO-004 / {page+1} of 2')
        c.setFont('Helvetica', 10)
        c.drawString(40, 525, 'TEST ONLY - NOT FOR CUSTOMS FILING - ALL PARTIES AND CODES ARE FICTIONAL')
        c.setFillColorRGB(0, 0, 0)
        values = ['Consignee: DEMO SOUTH IMPORTS', 'Manufacturer: DEMO SOUTH WORKS',
                  'Ship to: Australia (AU)', 'Terms: CIF', 'Currency: USD', 'Payment: T/T'] if page == 0 else [
                  'FTA preference requested: NO', 'HS code: 9503000000',
                  'Goods: PARTS OF TOYS | Trade name: TOY COMPONENTS', 'Origin: KR',
                  'Gross weight: 40.00 KG', 'Total net weight: 35.00 KG', 'Packages: 8 cartons']
        for n, value in enumerate(values):
            c.drawString(40, 494 - n * 22, value)
        xs = [40, 405, 555, 700]
        c.setFont('Helvetica-Bold', 11)
        for x, heading in zip(xs, ['Product details', 'Unit price', 'Line total', 'Quantity']):
            c.drawString(x, 305, heading)
        c.line(40, 294, 795, 294)
        c.setFont('Helvetica', 11)
        for n, item in enumerate(items[page*2:page*2+2]):
            for x, key in zip(xs, ['규격1', '단가', '금액', '수량']):
                c.drawString(x, 264-n*38, item[key])
        # Explicit stop before unrelated footer text.
        c.drawString(40, 180, 'Total amount: USD 12,500.00')
        if page == 1:
            c.drawString(40, 155, 'Freight: USD 0.00')
            c.drawString(40, 130, 'Other charges: USD 0.00')
        c.setFont('Helvetica', 9)
        c.drawString(40, 60, 'Item net weights and customs origin codes are unspecified; human review remains required.')
        c.showPage()
    c.save()
    doc = pdfium.PdfDocument(source.getvalue())
    out = ROOT / 'output/pdf/DEMO-004.pdf'
    final = canvas.Canvas(str(out), pagesize=(842, 595))
    for page in doc:
        bitmap = page.render(scale=2)
        final.drawImage(ImageReader(bitmap.to_pil().convert('RGB')), 0, 0, width=842, height=595)
        final.showPage()
        bitmap.close()
        page.close()
    final.save()
    doc.close()
    (ROOT / 'docs/demo-cases/DEMO-004-expected.json').write_text(json.dumps({
        'case': 'DEMO-004', 'synthetic': True, 'profile': profile, 'common': common,
        'items': items, 'description': 'Landscape two-page repeated table, aliases and comma amounts',
        'limitations': 'Authored after rules were fixed by the same agent; controlled test, not blind external validation.'
    }, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    main()
