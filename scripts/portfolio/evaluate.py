"""Evaluate frozen synthetic cases using real local OCR, without changing the parser.

Run from any directory: backend/.venv/bin/python scripts/portfolio/evaluate.py
Results are observations, not a universal accuracy score or filing approval.
"""
import argparse
import hashlib
from datetime import datetime, timezone
import json
import platform
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))

import pdfplumber
from app.services.preparation import COLUMNS, prepare_pdf


def normalized(value):
    return '' if value is None else str(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'docs/demo-cases/improved')
    parser.add_argument('--cases', type=int, nargs='+', default=[1, 2, 3, 4])
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    reports = []
    for number in args.cases:
        case = f'DEMO-{number:03}'
        if number == 1:
            source = json.loads((ROOT / 'docs/demo-case/expected.json').read_text())
            common = {k: normalized(v['value']) for k, v in source['common'].items()}
            profile = {k: v['value'] for k, v in source['common'].items() if 'demo profile' in v['source']}
            path = ROOT / 'output/pdf/synthetic-shipping-scan.pdf'
        else:
            source = json.loads((ROOT / f'docs/demo-cases/{case}-expected.json').read_text())
            common, profile = source['common'], source['profile']
            path = ROOT / f'output/pdf/{case}.pdf'
        with pdfplumber.open(path) as pdf:
            assert not any(p.extract_text() for p in pdf.pages), 'Input must be image only'
        runs = [prepare_pdf(path.read_bytes(), profile) for _ in range(3)]
        actual = runs[0]
        cells = []
        for key, expected in common.items():
            value = actual['common'][key]['value']
            cells.append({'scope': 'common', 'field': key, 'expected': expected, 'actual': value,
                          'match': value == expected, 'source': actual['common'][key]['kind']})
        for index, expected_row in enumerate(source['items']):
            for key in COLUMNS[:12]:
                expected = normalized(expected_row[key])
                # A missing row is a failure, even when its expected cell is blank.
                value = actual['items'][index][key]['value'] if index < len(actual['items']) else None
                cells.append({'scope': 'item', 'row': index + 1, 'field': key, 'expected': expected,
                              'actual': value, 'match': value == expected})
        consistent = all(r['common'] == actual['common'] and r['items'] == actual['items'] for r in runs)
        record = {
            'case': case, 'input': str(path.relative_to(ROOT)),
            'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'expected_rows': len(source['items']), 'actual_rows': len(actual['items']),
            'extra_rows': max(0, len(actual['items']) - len(source['items'])),
            'common_matches': sum(c['match'] for c in cells if c['scope'] == 'common'),
            'common_total': len(common),
            'item_matches': sum(c['match'] for c in cells if c['scope'] == 'item'),
            'item_total': len(source['items']) * 12,
            'nonblank_matches': sum(c['match'] for c in cells if c['expected'] != ''),
            'nonblank_total': sum(c['expected'] != '' for c in cells),
            'elapsed_seconds': [r['elapsed_seconds'] for r in runs],
            'median_seconds': statistics.median(r['elapsed_seconds'] for r in runs),
            'repeat_values_identical': consistent, 'issues': actual['issues'], 'cells': cells,
            'manual_seconds': None, 'assisted_total_seconds': None, 'human_corrected_cells': None,
        }
        reports.append(record)
        # Retain OCR/provenance for failure inspection, omit rendered images.
        for p in actual['pages']:
            p.pop('image', None)
        (args.output_dir / f'{case}-actual.json').write_text(json.dumps(actual, ensure_ascii=False, indent=2) + '\n')
        print(case, record['common_matches'], '/', len(common), record['item_matches'], '/', record['item_total'], 'rows',record['actual_rows'], 'seconds',record['elapsed_seconds'])
    result = {'evaluated_at_utc': datetime.now(timezone.utc).isoformat(),
              'parser_sha256': hashlib.sha256((ROOT / 'backend/app/services/preparation.py').read_bytes()).hexdigest(),
              'platform': platform.platform(), 'python': platform.python_version(),
              'method': 'Fixed synthetic image PDFs, 3 sequential local OCR runs each; first output scored; cases 1-3 are development/regression cases, case 4 is a new controlled combination test',
              'limitations': ['Includes blank and repeated cells; nonblank counts also provided.',
                             'No real customer files, no manual time measurement, no ecom integration.',
                             'Three repetitions measure stability, not independent documents.'],
              'cases': reports}
    (args.output_dir / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
