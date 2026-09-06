# 합성 이미지 문서 검증과 매핑 개선

처음 세 문서에서 OCR 누락과 매핑 실패를 구분한 뒤, 라벨 동의어와 표 헤더 연결을 보완했다. 이후 새 조합 문서 DEMO-004를 추가했다. 모든 문서는 합성이며 실제 고객 양식이나 일반 OCR 정확도를 대표하지 않는다.

| 사례 | 조건 | 개선 전 공통 / 품목 | 개선 후 공통 / 품목 | 행 | 처리 중앙값 |
|---|---|---|---|---|---|
| DEMO-001 | 2쪽 Invoice + Packing List | 16/16 · 143/144 | 16/16 · 143/144 | 12/12 | 0.43초 |
| DEMO-002 | Amount/Qty/Unit 열 순서 변경 | 16/16 · 36/36 | 16/16 · 36/36 | 3/3 | 0.26초 |
| DEMO-003 | Consignee/Ship to/Invoice value 등 | 13/16 · 0/36 | 16/16 · 36/36 | 3/3 | 0.27초 |
| DEMO-004 | 2쪽 반복 표 헤더·열 순서·천 단위 구분 | 미실행 | 16/16 · 48/48 | 4/4 | 0.39초 |

공통 16개 중 4개는 명시적인 가상 설정값이다. 품목은 12열 기준이며 공란과 반복값이 포함된다. 미확인 원산지코드는 이 대조 범위 밖이다. 각 문서를 3회 처리해 값이 동일했으며, 독립 문서 수는 4건이다. 시간은 OCR·매핑·이미지 생성만 포함하고 사람 검토와 ecom 작업은 제외한다. 수작업 대비 시간 절감은 미측정이다.

## 무엇을 고쳤는가

DEMO-003은 글자를 읽고도 기존 Buyer/Destination/Total amount 및 표 제목 규칙과 연결되지 않았다. 동의어를 추가하고 열 위치 기반 매핑을 유지했으며, 다른 값 충돌과 합계 행 경계도 회귀 테스트로 확인했다. 이 문서는 이제 개선에 사용한 자료이며 독립 평가 자료로 주장하지 않는다.

DEMO-004는 규칙 수정 후 생성한 통제된 조합 시험이다. 동일한 개발 과정에서 만든 문서이므로 외부 블라인드 검증이 아니다. DEMO-001의 수량 11 누락은 여전히 남아 있고 공란·확인 대상으로 표시한다. OCR 누락을 추측값으로 숨기지 않는다.

## 재현

macOS에서 `./scripts/setup-ocr` 실행 후:

```bash
backend/.venv/bin/python scripts/portfolio/evaluate.py
```

기본 출력은 `docs/demo-cases/improved/`이다. `--cases 4 --output-dir /tmp/customs-evaluation`로 별도 경로에 한 사례만 실행할 수도 있다. PDF·파서 SHA-256과 실행 환경·시간·칸별 정답 대조를 기록한다.

- [개선 전 기록](baseline/results.json)과 [개선 후 기록](improved/results.json). 상위 폴더의 기존 results.json도 최초 평가 기록으로 보존했다.
- 정답: [001](../demo-case/expected.json), [002](DEMO-002-expected.json), [003](DEMO-003-expected.json), [004](DEMO-004-expected.json).
- PDF: `output/pdf/synthetic-shipping-scan.pdf`, `DEMO-002.pdf`, `DEMO-003.pdf`, `DEMO-004.pdf`.
- 재생성 도구: `scripts/portfolio/generate_cases.py`, `generate_holdout.py`. 선택 의존성 reportlab·pypdfium2·Pillow 필요. 재생성하면 OCR을 다시 평가한다.

## 설치 검증

같은 Mac의 별도 소스 복사본에서 기존 .venv·node_modules·DB·업로드·OCR 바이너리 없이 시작했다. Python 3.12를 지정해 bootstrap → check → setup-ocr → DEMO-004 평가를 실행했다. 테스트 38개·lint·빌드가 통과했고, 새 OCR 바이너리에서 공통 16/16·품목 48/48을 확인했다. 다른 OS나 다른 사용자의 설치를 검증한 것은 아니다. Ubuntu CI는 macOS OCR을 실행하지 않는다. 빌드에는 큰 번들 경고가 남는다.
