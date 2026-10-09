"""Field provenance and failure handling for the local prototype."""
from copy import deepcopy

import httpx
import pytest

from app.main import app
from app.services.preparation import parse_pages


def pages():
    rows = [
        [(0.1, 'Buyer: OTHER CUSTOMER')],
        [(0.1, 'Seller / Manufacturer: OTHER MAKER')],
        [(0.1, 'Total amount: USD 37.50')],
        [(0.1, 'FTA preference requested: YES')],
        [(0.1, 'Description'), (0.55, 'Qty'), (0.65, 'Unit USD'), (0.8, 'Amount USD')],
        [(0.1, 'Independent Widget A'), (0.55, '3'), (0.65, '12.50'), (0.8, '37.50')],
    ]
    return [{'number': 1, 'segments': [dict(text=text, x=x, y=0.9-i*0.05, height=0.01, confidence=1) for i,row in enumerate(rows) for x,text in row]}]


def test_extracts_changed_values_and_keeps_provenance():
    result = parse_pages(pages(), {'구매자코드': 'PROFILE-002'})
    assert result['common']['구매자']['value'] == 'OTHER CUSTOMER'
    assert result['common']['구매자']['page'] == 1
    assert result['common']['구매자코드']['kind'] == 'profile'
    assert result['common']['목적국']['value'] == ''
    assert result['items'][0]['규격1']['value'] == 'Independent Widget A'
    assert result['items'][0]['금액']['value'] == '37.50'
    assert result['items'][0]['순중량']['value'] == ''
    assert any('FTA Y' in issue for issue in result['issues'])


def test_missing_quantity_preserves_row_and_flags_failure():
    source = pages()
    source[0]['segments'] = [s for s in source[0]['segments'] if s['text'] != '3']
    result = parse_pages(source)
    assert len(result['items']) == 1
    assert result['items'][0]['수량']['value'] == ''
    assert result['items'][0]['단가']['value'] == '12.50'
    assert any('숫자 판독 실패' in issue for issue in result['issues'])


def test_conflicting_buyer_is_not_silently_selected():
    source = pages()
    second = deepcopy(source[0]); second['number'] = 2
    second['segments'] = [dict(text='Buyer: CONFLICT', x=0.1, y=0.9, height=0.01, confidence=1)]
    source.append(second)
    result = parse_pages(source)
    assert result['common']['구매자']['value'] == ''
    assert result['common']['구매자']['kind'] == 'conflict'


def test_blank_ocr_is_not_success():
    result = parse_pages([{'number': 1, 'segments': []}])
    assert result['items'] == []
    assert any('읽지 못' in issue for issue in result['issues'])


def test_amount_mismatch_and_unknown_fta_are_visible():
    source = pages()
    for s in source[0]['segments']:
        if s['text'] == '37.50': s['text'] = '38.50'
        if s['text'].startswith('FTA preference'): s['text'] = 'No certificate attached'
    result = parse_pages(source)
    assert result['items'][0]['FTA발급여부']['value'] == ''
    assert any('합계' in issue for issue in result['issues'])
    assert any('수량×단가' in issue for issue in result['issues'])


@pytest.mark.asyncio
async def test_upload_validation_and_profile_no_arbitrary_paths(monkeypatch):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        r = await client.post('/api/preparation/pdf', files={'file': ('x.pdf', b'not pdf')})
        assert r.status_code == 415
        r = await client.post('/api/preparation/pdf', files={'file': ('x.pdf', b'%PDF-')}, data={'profile': '{"path":"/private/data"}'})
        assert r.status_code == 422
        r = await client.post('/api/preparation/pdf', files={'file': ('x.pdf', b'%PDF-' + b'0' * (10 * 1024 * 1024))})
        assert r.status_code == 413
        def unavailable(*args): raise RuntimeError('OCR unavailable')
        monkeypatch.setattr('app.api.preparation.prepare_pdf', unavailable)
        r = await client.post('/api/preparation/pdf', files={'file': ('x.pdf', b'%PDF-')})
        assert r.status_code == 503


def test_alias_headers_reordered_columns_and_summary_boundary():
    source = pages()
    replacements = {'Buyer: OTHER CUSTOMER': 'Consignee: OTHER CUSTOMER',
                    'Total amount: USD 37.50': 'Invoice value: USD 37.50',
                    'Description': 'Product details', 'Qty': 'Quantity',
                    'Unit USD': 'Price', 'Amount USD': 'Line total'}
    for segment in source[0]['segments']:
        segment['text'] = replacements.get(segment['text'], segment['text'])
        if segment['x'] == 0.55:
            segment['x'] = 0.8
        elif segment['x'] == 0.8:
            segment['x'] = 0.55
    source[0]['segments'].append(dict(text='Invoice value: USD 37.50', x=0.1,
                                    y=0.5, height=0.01, confidence=1))
    result = parse_pages(source)
    assert result['common']['구매자']['value'] == 'OTHER CUSTOMER'
    assert len(result['items']) == 1
    assert result['items'][0]['수량']['value'] == '3'
    assert result['items'][0]['금액']['value'] == '37.50'


def test_alias_conflict_is_not_silently_selected():
    source = pages()
    source.append({'number': 2, 'segments': [dict(text='Consignee: DIFFERENT',
                   x=0.1, y=0.9, height=0.01, confidence=1)]})
    assert parse_pages(source)['common']['구매자']['kind'] == 'conflict'
