"""Local OCR + explicit field mapping prototype. No filing or database writes."""
import base64
import io
import json
import re
import subprocess
import tempfile
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pypdfium2 as pdfium

COMMON = ['환급신청인', '간이자동정액환급여부', '구매자코드', '목적국', '구매자', '제조자', '거래구분', '결제방법', '인도조건', '통화단위', '운임비', '기타금액', '총금액', '총중량', '전체순중량', '카톤수']
COLUMNS = ['규격1', '규격2', '규격3', '수량', '단가', '금액', 'FTA발급여부', 'FTA발급협정코드', '세번부호', '품명', '거래품명', '순중량', '원산지', '원산지코드']
PROFILE_KEYS = {'환급신청인', '간이자동정액환급여부', '구매자코드', '거래구분'}
NUMBER = r'([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)'
BINARY = Path(__file__).resolve().parents[2] / '.local-bin' / 'vision-ocr'


def cell(value: str = '', page: int | None = None, evidence: str = '', kind: str = 'missing') -> dict:
    return {'value': value, 'page': page, 'evidence': evidence, 'kind': kind}


def grouped_lines(pages: list[dict]) -> list[dict]:
    lines = []
    for page in pages:
        groups: list[list[dict]] = []
        for segment in sorted(page['segments'], key=lambda s: -s['y']):
            group = next((g for g in groups if abs(g[0]['y'] - segment['y']) < 0.008), None)
            if group is None:
                groups.append([segment])
            else:
                group.append(segment)
        for group in groups:
            parts = sorted(group, key=lambda s: s['x'])
            lines.append({'page': page['number'], 'text': ' | '.join(s['text'] for s in parts), 'parts': parts})
    return lines


def decimal(value: str) -> Decimal | None:
    if not re.fullmatch(NUMBER, value):
        return None
    try:
        return Decimal(value.replace(',', ''))
    except InvalidOperation:
        return None


def parse_pages(pages: list[dict], profile: dict[str, str] | None = None) -> dict:
    lines = grouped_lines(pages)
    common = {key: cell() for key in COMMON}
    issues: list[str] = []
    for key, value in (profile or {}).items():
        if key in PROFILE_KEYS and value:
            common[key] = cell(value, evidence='사용자가 적용한 설정값 (PDF 추출 아님)', kind='profile')

    def extract(pattern: str, transform=None) -> dict:
        matches = []
        for line in lines:
            match = re.search(pattern, line['text'], re.I)
            if match:
                value = match.group(1).strip()
                if transform:
                    value = transform(value)
                matches.append(cell(value, line['page'], line['text'], 'document'))
        unique = {m['value'] for m in matches}
        if len(unique) > 1:
            issues.append('서류 간 값 충돌: ' + ' / '.join(sorted(unique)))
            return cell(evidence=' / '.join(m['evidence'] for m in matches), kind='conflict')
        return matches[0] if matches else cell()

    patterns = {
        '구매자': r'^(?:Buyer|Consignee)\s*:\s*(.+)$',
        '제조자': r'^(?:Seller\s*/\s*)?Manufacturer\s*:\s*(.+)$',
        '목적국': r'^(?:Destination|Ship to)\s*:\s*.*?\(([A-Z]{2})\)',
        '인도조건': r'\bTerms\s*:\s*(EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP)\b',
        '통화단위': r'\bCurrency\s*:\s*([A-Z]{3})\b',
        '결제방법': r'\bPayment\s*:\s*([A-Z/]+)\b',
        '총금액': r'\b(?:Total (?:invoice )?amount|Invoice value)\s*:\s*(?:[A-Z]{3}\s*)?' + NUMBER,
        '운임비': r'\bFreight(?: billed on invoice)?\s*:\s*(?:[A-Z]{3}\s*)?' + NUMBER,
        '기타금액': r'\bOther charges\s*:\s*(?:[A-Z]{3}\s*)?' + NUMBER,
        '총중량': r'\bGross weight\s*:\s*' + NUMBER + r'\s*KG\b',
        '전체순중량': r'\bTotal net weight\s*:\s*' + NUMBER + r'\s*KG\b',
        '카톤수': r'\bPackages\s*:\s*(\d+)\s*cartons\b',
    }
    for key, pattern in patterns.items():
        common[key] = extract(pattern, (lambda v: 'TT' if v.upper() == 'T/T' else v) if key == '결제방법' else None)
    shared = {
        '세번부호': extract(r'^HS(?: code| as supplied by seller)?\s*:\s*(\d{6,10})\b'),
        '품명': extract(r'^Goods\s*:\s*(.+?)\s+[|I]\s+Trade name\s*:'),
        '거래품명': extract(r'\bTrade name\s*:\s*(.+)$'),
        'FTA발급여부': extract(r'\bFTA preference requested\s*:\s*(YES|NO|Y|N)\b', lambda v: 'Y' if v.upper() in {'YES', 'Y'} else 'N'),
        'FTA발급협정코드': extract(r'\bFTA agreement code\s*:\s*(\d+)\b'),
        '원산지': extract(r'^Origin(?: statement for this fictional shipment)?\s*:\s*([A-Z]{2})\b'),
    }
    headers_patterns = {
        '규격1': r'\b(?:Description|Product details)\b',
        '수량': r'\b(?:Qty|Quantity)\b',
        '단가': r'\b(?:Unit(?: price)?|Price)\b',
        '금액': r'\b(?:Amount|Line total)\b',
    }
    items = []
    table = None
    for line in lines:
        text = line['text']
        if all(re.search(pattern, text, re.I) for pattern in headers_patterns.values()):
            parts = line['parts']
            headers = {}
            for part in parts:
                for label, pattern in headers_patterns.items():
                    if re.search(pattern, part['text'], re.I):
                        headers[label] = part['x']
            table = (line['page'], headers) if len(headers) == 4 else None
            if table is None:
                issues.append(f"{line['page']}페이지 표 열 구분 실패: 원문 확인 필요")
            continue
        if table is None:
            continue
        if line['page'] != table[0] or re.match(r'^(?:Total|Grand total|Invoice value|Freight|Note|All names)', text, re.I):
            table = None
            continue
        row = {key: cell() for key in COLUMNS}
        for key, value in shared.items():
            row[key] = value.copy()
        for key in ['규격2', '규격3', '순중량']:
            row[key] = cell(evidence='빈칸 유지; 미제공 값을 추정하지 않음', kind='blank')
        buckets = {key: [] for key in table[1]}
        for part in line['parts']:
            key = min(table[1], key=lambda k: abs(table[1][k] - part['x']))
            buckets[key].append(part['text'])
        for key, parts in buckets.items():
            if parts:
                row[key] = cell(' '.join(parts), line['page'], text, 'document')
        if shared['FTA발급여부']['value'] == 'N':
            if shared['FTA발급협정코드']['value']:
                issues.append('FTA N과 협정코드가 함께 기재됨: 원문 확인 필요')
            row['FTA발급협정코드'] = cell(evidence='서류에 FTA N 명시', kind='blank')
        items.append(row)
    if not items:
        issues.append('품목 표를 읽지 못했습니다. 지원 열: Description / Qty / Unit / Amount. 빈 결과는 성공이 아닙니다.')
    for key, value in common.items():
        if not value['value']:
            issues.append(f'공통항목 {key}: 값 또는 설정 확인 필요')
    for index, row in enumerate(items, 1):
        for key in ['규격1', '수량', '단가', '금액', '세번부호', '품명', '거래품명', 'FTA발급여부', '원산지', '원산지코드']:
            if not row[key]['value']:
                issues.append(f'{index}행 {key}: 확인 필요')
        qty, price, amount = (decimal(row[key]['value']) for key in ['수량', '단가', '금액'])
        if any(v is None for v in (qty, price, amount)):
            issues.append(f'{index}행 숫자 판독 실패: 수량·단가·금액을 대조하세요')
        elif qty <= 0 or price < 0 or amount < 0 or abs(qty * price - amount) > Decimal('0.01'):
            issues.append(f'{index}행 수량×단가와 금액 또는 부호 확인 필요')
        if row['FTA발급여부']['value'] == 'Y' and not row['FTA발급협정코드']['value']:
            issues.append(f'{index}행 FTA Y: 협정코드 확인 필요')
    amounts = [decimal(row['금액']['value']) for row in items]
    total = decimal(common['총금액']['value'])
    if amounts and all(v is not None for v in amounts) and total is not None:
        if sum(amounts) != total:
            issues.append('품목 금액 합계와 총금액 불일치')
    if not any(page['segments'] for page in pages):
        issues.append('OCR에서 텍스트를 읽지 못했습니다.')
    return {'common': common, 'items': items, 'issues': list(dict.fromkeys(issues)),
            'pages': [{'number': p['number'], 'text': '\n'.join(l['text'] for l in lines if l['page'] == p['number'])} for p in pages],
            'engine': 'Apple Vision OCR + 명시적 항목 규칙 (대표 영문 양식 시제품)',
            'status': 'draft', 'columns': COLUMNS}


def prepare_pdf(content: bytes, profile: dict[str, str]) -> dict:
    if not BINARY.is_file():
        raise RuntimeError('로컬 OCR 준비가 필요합니다: ./scripts/setup-ocr')
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='customs-ocr-') as directory:
        path = Path(directory) / 'input.pdf'
        path.write_bytes(content)
        try:
            process = subprocess.run([str(BINARY), str(path)], capture_output=True, timeout=120, check=True)
        except subprocess.TimeoutExpired as error:
            raise ValueError('OCR 제한시간을 초과했습니다. 문서를 나눠 주세요.') from error
        except subprocess.CalledProcessError as error:
            raise ValueError('PDF를 읽지 못했습니다. 암호 없는 1~12페이지 PDF인지 확인하세요.') from error
        result = parse_pages(json.loads(process.stdout), profile)
        document = pdfium.PdfDocument(content)
        try:
            for page_data in result['pages']:
                page = document[page_data['number'] - 1]
                try:
                    bitmap = page.render(scale=min(1.5, 1100 / page.get_width()))
                    try:
                        image = bitmap.to_pil().convert('RGB')
                        stream = io.BytesIO()
                        image.save(stream, format='JPEG', quality=80)
                        page_data['image'] = 'data:image/jpeg;base64,' + base64.b64encode(stream.getvalue()).decode()
                    finally:
                        bitmap.close()
                finally:
                    page.close()
        finally:
            document.close()
    result['elapsed_seconds'] = round(time.monotonic() - started, 2)
    return result
